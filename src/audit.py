"""Pure HTML analysis helpers: checks, contacts, people, scoring and pitch templates."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

YEAR = datetime.now(timezone.utc).year

# ---------------------------------------------------------------- URL helpers

def normalize_url(raw: str) -> str | None:
    s = (raw or '').strip().strip('<>"\'')
    if not s or ' ' in s.split('/')[0]:
        return None
    if s.startswith('//'):
        s = 'https:' + s
    if not re.match(r'^https?://', s, re.I):
        s = 'https://' + s
    p = urlparse(s)
    host = (p.hostname or '').lower()
    if '.' not in host or len(host) < 4:
        return None
    return f'{p.scheme.lower()}://{host}{p.path or "/"}' + (f'?{p.query}' if p.query else '')


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    host = (urlparse(url if '://' in url else 'https://' + url).hostname or '').lower()
    return host[4:] if host.startswith('www.') else host or None


SOCIAL_HOSTS = ('facebook.com', 'instagram.com', 'linkedin.com', 'twitter.com', 'x.com', 'youtube.com', 'tiktok.com',
                'yelp.', 'pinterest.', 'linktr.ee', 'business.site', 'g.page', 'google.com', 'goo.gl', 'wa.me')


def is_social_url(url: str) -> bool:
    d = domain_of(url) or ''
    return any(d == h or d.endswith('.' + h) or (h.endswith('.') and h in d) for h in SOCIAL_HOSTS)


# ---------------------------------------------------------------- signature detection

def _has(html: str, pats: list[str]) -> bool:
    return any(p in html for p in pats)


ANALYTICS = {
    'Google Analytics 4': [r'gtag/js\?id=G-', r"gtag\(\s*['\"]config['\"]\s*,\s*['\"]G-"],
    'Google Analytics (Universal)': [r"\bUA-\d{4,10}-\d{1,4}\b", r'google-analytics\.com/(?:analytics|ga)\.js'],
    'Google Tag Manager': [r'googletagmanager\.com/gtm\.js', r"\bGTM-[A-Z0-9]{4,9}\b"],
    'Microsoft Clarity': [r'clarity\.ms/tag'],
    'Hotjar': [r'static\.hotjar\.com', r'hotjar\.com/c/hotjar'],
    'Plausible': [r'plausible\.io/js'],
}
AD_PIXELS = {
    'Meta Pixel': [r'connect\.facebook\.net/[^"\']*/fbevents\.js', r"fbq\(\s*['\"]init['\"]"],
    'TikTok Pixel': [r'analytics\.tiktok\.com', r'ttq\.load\('],
    'Google Ads tag': [r"\bAW-\d{6,12}\b", r'googleadservices\.com/pagead/conversion'],
    'LinkedIn Insight': [r'snap\.licdn\.com/li\.lms-analytics', r'_linkedin_partner_id'],
    'Pinterest Tag': [r's\.pinimg\.com/ct/core\.js', r"pintrk\(\s*['\"]load"],
    'Microsoft Ads (UET)': [r'bat\.bing\.com/bat\.js'],
}
BOOKING = {
    'Calendly': ['calendly.com/'], 'Acuity': ['acuityscheduling.com', 'as.me/'], 'Square Appointments': ['squareup.com/appointments', 'book.squareup.com'],
    'Booksy': ['booksy.com'], 'Vagaro': ['vagaro.com'], 'Fresha': ['fresha.com'], 'Mindbody': ['mindbodyonline.com', 'mindbody.io'],
    'Setmore': ['setmore.com'], 'SimplyBook': ['simplybook.'], 'OpenTable': ['opentable.com'], 'Resy': ['resy.com'],
    'Zocdoc': ['zocdoc.com'], 'Housecall Pro': ['housecallpro.com'], 'Jobber': ['getjobber.com', 'clienthub.getjobber'],
    'ServiceTitan': ['servicetitan.com'], 'Schedulicity': ['schedulicity.com'], 'GlossGenius': ['glossgenius.com'],
    'Tock': ['exploretock.com'], 'Yelp Reservations': ['yelp.com/reservations'], 'Wix Bookings': ['wix-bookings', 'bookings-checkout'],
    'Squarespace Scheduling': ['squarespacescheduling.com'], 'Zenoti': ['zenoti.com'], 'Boulevard': ['joinblvd.com', 'blvd.co'],
    'LocalMed': ['localmed.com'], 'NexHealth': ['nexhealth.com'], 'Podium': ['podium.com'], 'Toast': ['toasttab.com'],
    'ChowNow': ['chownow.com'], 'DoorDash storefront': ['order.online'],
}
CHAT = {
    'Intercom': ['widget.intercom.io', 'js.intercomcdn.com'], 'Drift': ['js.driftt.com', 'drift.com/'], 'Tawk.to': ['embed.tawk.to'],
    'Crisp': ['client.crisp.chat'], 'LiveChat': ['cdn.livechatinc.com'], 'Zendesk': ['static.zdassets.com', 'zopim'],
    'HubSpot Chat': ['js.usemessages.com', 'hs-scripts.com'], 'Tidio': ['code.tidio.co'], 'Olark': ['static.olark.com'],
    'Podium Webchat': ['connect.podium.com'], 'Birdeye': ['birdeye.com/embed'], 'WhatsApp': ['wa.me/', 'api.whatsapp.com/send'],
    'Facebook Messenger': ['m.me/', 'xfbml.customerchat'], 'Smith.ai': ['smith.ai'], 'Freshchat': ['wchat.freshchat.com'],
}
FORM_TOOLS = ['typeform.com', 'jotform', 'wpforms', 'gform_wrapper', 'gravityforms', 'wpcf7', 'hsforms', 'hbspt.forms',
              'formstack', 'cognitoforms', 'forms.gle', 'docs.google.com/forms', 'ninja-forms', 'elementor-form', 'wixforms',
              'form-block', 'fluentform', 'formidable', 'sqs-block-form', '123formbuilder', 'paperform']
BUILDERS = [
    ('Wix', ['static.wixstatic.com', 'wix.com/', '_wixCIDX', 'wixsite.com']),
    ('Squarespace', ['squarespace.com', 'static1.squarespace', 'sqs-block']),
    ('Shopify', ['cdn.shopify.com', 'Shopify.theme', 'myshopify.com']),
    ('Webflow', ['webflow.com', 'wf-page', 'data-wf-site']),
    ('GoDaddy Website Builder', ['img1.wsimg.com', 'websites.godaddy', 'godaddysites.com']),
    ('Weebly', ['weebly.com', 'editmysite.com']),
    ('Duda', ['multiscreensite.com', 'dudaone', 'dmCacheClear', 'irp.cdn-website.com']),
    ('Framer', ['framerusercontent.com', 'framer.com/']),
    ('Carrd', ['carrd.co']),
    ('Jimdo', ['jimdo', 'jimstatic.com']),
    ('Site123', ['site123.me', 'cdn-cms.f-static']),
    ('Google Sites', ['sites.google.com', 'gstatic.com/atari']),
    ('HubSpot CMS', ['hs-sites.com', 'hubspotusercontent']),
    ('Ghost', ['ghost.io', 'content="Ghost']),
    ('Joomla', ['/media/jui/', 'content="Joomla']),
    ('Drupal', ['drupal.js', 'Drupal.settings', 'content="Drupal']),
    ('WordPress', ['wp-content/', 'wp-includes/', 'content="WordPress']),
]


_RX_CACHE: dict[int, list[tuple[str, re.Pattern[str]]]] = {}


def _lower_pattern(p: str) -> str:
    """Lower-case the literal letters of a regex (not escapes like \\d or \\b). Searching the lower-cased page with it
    gives the same answer as re.I on the page, but CPython's re is about 10x faster without IGNORECASE."""
    out, esc = [], False
    for ch in p:
        if esc:
            assert not ch.isupper(), f'upper-case escape not supported: {p}'
            out.append(ch)
            esc = False
        elif ch == '\\':
            out.append(ch)
            esc = True
        else:
            out.append(ch.lower())
    return ''.join(out)


def _anchor(p: str) -> str | None:
    """Longest literal that every match of regex p must contain (top level only), or None. Used as a fast
    'substring in page' pre-check so the regex only runs on pages that can match."""
    runs, cur, depth, i = [], '', 0, 0
    while i < len(p):
        ch = p[i]
        if ch == '\\' and i + 1 < len(p):
            nxt = p[i + 1]
            if nxt.isalnum():  # \b \d \s ... are classes, not literals
                runs.append(cur); cur = ''
            elif depth == 0:
                cur += nxt
            i += 2
            continue
        if ch == '|' and depth == 0:
            return None
        if ch == '(':
            depth += 1; runs.append(cur); cur = ''
        elif ch == ')':
            depth -= 1
        elif ch == '[':
            runs.append(cur); cur = ''
            j = p.index(']', i + 1 if p[i + 1] != ']' else i + 2)
            i = j
        elif ch in '*+?{':
            if ch in '?*' or (ch == '{' and re.match(r'\{0', p[i:])):
                cur = cur[:-1]
            elif ch == '{':
                cur = cur[:-1]
            runs.append(cur); cur = ''
            if ch == '{':
                i = p.index('}', i)
        elif ch in '.^$':
            runs.append(cur); cur = ''
        elif depth == 0:
            cur += ch
        i += 1
    runs.append(cur)
    best = max(runs, key=len)
    return best if len(best) >= 3 else None


def _compiled(table: dict[str, list[str]]) -> list[tuple[str, list[tuple[str | None, re.Pattern[str]]]]]:
    # per pattern: (literal pre-check, regex for the lower-cased page). Same result as re.I on the raw page.
    key = id(table)
    if key not in _RX_CACHE:
        out = []
        for name, pats in table.items():
            lp = [_lower_pattern(p) for p in pats]
            out.append((name, [(_anchor(x), re.compile(x)) for x in lp]))
        _RX_CACHE[key] = out
    return _RX_CACHE[key]


_LIT_CACHE: dict[int, list[tuple[str, list[str]]]] = {}


def _detect(html_lower: str, table: dict[str, list[str]], regex: bool = False) -> list[str]:
    """html_lower must be the lower-cased page."""
    if regex:
        return [name for name, pats in _compiled(table)
                if any((a is None or a in html_lower) and rx.search(html_lower) for a, rx in pats)]
    key = id(table)
    if key not in _LIT_CACHE:
        _LIT_CACHE[key] = [(name, [p.lower() for p in pats]) for name, pats in table.items()]
    return [name for name, pats in _LIT_CACHE[key] if any(p in html_lower for p in pats)]


def detect_builder(html: str, html_lower: str) -> tuple[str | None, str | None]:
    gen = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', html, re.I) or \
        re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']generator', html, re.I)
    generator = gen.group(1).strip()[:80] if gen else None
    for name, pats in BUILDERS:
        if any(p.lower() in html_lower for p in pats):
            return name, generator
    if generator:
        return generator.split()[0], generator
    return None, generator


# ---------------------------------------------------------------- contacts

EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,190}\.[A-Za-z]{2,24}')
BAD_EMAIL_PARTS = ('example.', 'sentry', 'wixpress', '@2x', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', 'yourdomain',
                   'domain.com', 'email.com', 'godaddy.com', 'sentry.io', 'squarespace.com', 'wix.com', 'schema.org',
                   'u003e', 'placeholder', '@sample', 'name@', 'user@', 'test@', 'john@doe', 'johndoe', 'jane@', 'xxx',
                   'mysite.com', 'company.com', 'website.com', 'shopify.com', 'cloudflare', 'w3.org', 'noreply', 'no-reply')
GENERIC_LOCAL = {'info', 'contact', 'hello', 'hi', 'office', 'admin', 'sales', 'support', 'help', 'booking', 'bookings',
                 'book', 'appointments', 'appointment', 'service', 'services', 'team', 'mail', 'email', 'enquiries',
                 'inquiries', 'enquiry', 'inquiry', 'guestcare', 'guest', 'guests', 'customercare', 'hola', 'howdy', 'team', 'staff', 'reception', 'frontdesk', 'front.desk', 'orders', 'order', 'care',
                 'customerservice', 'billing', 'accounts', 'accounting', 'marketing', 'jobs', 'careers', 'hr', 'general',
                 'studio', 'shop', 'store', 'events', 'press', 'media', 'reservations', 'webmaster', 'manager',
                 'contactus', 'customercare', 'dispatch', 'scheduling', 'schedule', 'estimates', 'quotes', 'quote',
                 'request', 'hola', 'connect', 'welcome', 'clinic', 'dental', 'practice', 'mgmt', 'management'}


def find_emails(s: str) -> list[str]:
    """EMAIL_RE.findall(s), but the regex only runs in a small window around each '@' (every match has exactly
    one '@'). Scanning the whole page with a pattern that starts with a character class was the slowest step."""
    out: list[str] = []
    last_end = 0
    i = s.find('@')
    while i != -1:
        start = max(last_end, i - 64)
        for m in EMAIL_RE.finditer(s, start, min(len(s), i + 216)):
            at = start + m.group(0).index('@') + (m.start() - start)
            if at == i:
                out.append(m.group(0))
                last_end = m.end()
                break
            if at > i:
                break
        i = s.find('@', i + 1)
    return out


def clean_email(e: str) -> str | None:
    e = e.strip().strip('.').lower()
    if e.startswith('mailto:'):
        e = e[7:]
    e = e.split('?')[0]
    if not EMAIL_RE.fullmatch(e) or any(b in e for b in BAD_EMAIL_PARTS):
        return None
    local, dom = e.rsplit('@', 1)
    if re.fullmatch(r'[0-9a-f]{16,}', local) or len(local) > 40:
        return None
    if dom.split('.')[-1] in ('png', 'jpg', 'gif', 'js', 'css', 'webp', 'svg'):
        return None
    return e


def email_kind(e: str) -> str:
    local = e.split('@')[0]
    base = re.sub(r'[\d_\-.]+$', '', local)
    return 'generic' if local in GENERIC_LOCAL or base in GENERIC_LOCAL else 'personal'


PHONE_RE = re.compile(r'(?:\+?1[\s.\-]?)?\(?\b[2-9]\d{2}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b|\+\d{1,3}[\s.\-]?\(?\d{1,4}\)?(?:[\s.\-]?\d{2,4}){2,4}')


def clean_phone(p: str) -> str | None:
    p = p.replace('tel:', '').replace('%20', ' ').strip()
    digits = re.sub(r'\D', '', p)
    if not 7 <= len(digits) <= 15 or len(set(digits)) < 3:
        return None
    return re.sub(r'\s+', ' ', p)[:30]


def extract_contacts(soup: BeautifulSoup, html: str, base_url: str) -> dict[str, Any]:
    emails: list[str] = []
    phones: list[str] = []
    socials: dict[str, str] = {}
    for a in soup.find_all('a', href=True):
        h = a['href'].strip()
        hl = h.lower()
        if hl.startswith('mailto:'):
            e = clean_email(h)
            if e:
                emails.append(e)
        elif hl.startswith('tel:'):
            ph = clean_phone(h)
            if ph:
                phones.append(ph)
        elif hl.startswith('http') or hl.startswith('//'):
            d = domain_of(h) or ''
            key = None
            if d.endswith('facebook.com') and '/sharer' not in hl and '/plugins' not in hl and '/tr?' not in hl:
                key = 'facebook'
            elif d.endswith('instagram.com') and '/p/' not in hl:
                key = 'instagram'
            elif d.endswith('linkedin.com') and '/share' not in hl:
                key = 'linkedin'
            elif d in ('twitter.com', 'x.com') and '/intent' not in hl and '/share' not in hl:
                key = 'x'
            elif d.endswith('youtube.com') and ('/channel' in hl or '/@' in hl or '/c/' in hl or '/user' in hl):
                key = 'youtube'
            elif d.endswith('tiktok.com') and '/@' in hl:
                key = 'tiktok'
            elif 'yelp.' in d and '/biz/' in hl:
                key = 'yelp'
            elif d.endswith('pinterest.com'):
                key = 'pinterest'
            elif d in ('wa.me', 'api.whatsapp.com'):
                key = 'whatsapp'
            elif d == 'nextdoor.com':
                key = 'nextdoor'
            if key and key not in socials:
                socials[key] = urljoin(base_url, h)[:300]
    text = soup.get_text(' ', strip=True)
    deob = re.sub(r'\s*[\[\(\{]\s*at\s*[\]\)\}]\s*', '@', text, flags=re.I)
    deob = re.sub(r'\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*', '.', deob, flags=re.I)
    for m in find_emails(deob):
        e = clean_email(m)
        if e:
            emails.append(e)
    for m in find_emails(html[:400000]):  # JSON-LD / data attributes
        e = clean_email(m)
        if e:
            emails.append(e)
    for m in PHONE_RE.findall(text[:200000]):
        ph = clean_phone(m)
        if ph:
            phones.append(ph)
    # de-dup phones by digits
    seen: set[str] = set()
    uphones = []
    for p in phones:
        k = re.sub(r'\D', '', p)[-10:]
        if k not in seen:
            seen.add(k)
            uphones.append(p)
    return {'emails': list(dict.fromkeys(emails)), 'phones': uphones[:8], 'socials': socials}


# ---------------------------------------------------------------- people

ROLE_WORDS = r'(?:Co[- ]?Founder|Founder|Owner|Co[- ]?Owner|Proprietor|CEO|Chief Executive Officer|President|Principal|' \
    r'Managing Director|Managing Partner|General Manager|Director|Head Chef|Executive Chef|Chef[- ]Owner|Lead Dentist|' \
    r'Practice Owner|Broker|Broker[- ]Owner|Realtor|Attorney|Partner|Operator|Manager|DDS|DMD|MD|DVM|DC|CPA|Esq\.?|' \
    r'Head Coach|Lead Stylist|Master Barber|Lead Technician|Licensed Contractor|Physician|Chiropractor|Veterinarian|Dentist|Therapist)'
NAME_TOKEN = r"[A-Z][a-z]{1,15}(?:[-'][A-Z][a-z]{1,15})?"
NAME = rf"{NAME_TOKEN}(?:\s+[A-Z]\.)?\s+{NAME_TOKEN}(?:\s+{NAME_TOKEN})?"
STOP = set('''Our The Contact About Home Services Service Team Free Call Get Book Read More Learn Meet Your We Us Welcome Why
What How Who When Where Privacy Policy Terms Copyright All Rights Reserved Menu Gallery Reviews Review Testimonials
Blog News Shop Store Cart Login Sign Up Hours Open Today Now New Best Top Local Family Professional Quality Customer
Customers Client Clients Free Estimate Estimates Request Quote Schedule Appointment Appointments Online Location
Locations Directions Map Email Phone Fax Address Street Suite Avenue Road Drive Boulevard Lane North South East West
Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September
October November December Inc LLC Ltd Co Company Group Dental Clinic Studio Salon Spa Restaurant Bar Grill Cafe Kitchen
Plumbing Heating Cooling Air Roofing Electric Electrical Construction Law Firm Office Center Centre Health Care Medical
Insurance Realty Real Estate Auto Repair Cleaning Landscaping Lawn Pest Control Fitness Gym Yoga Pilates Massage Beauty
Hair Nail Nails Barber Barbershop Pet Vet Animal Hospital Pizza Coffee Bakery Market Solutions Services Systems Agency
Marketing Design Digital Media Web Website Site Click Here View See Find Join Follow Like Share Subscribe Download
Board Certified Licensed Insured Award Winning Since Established Years Experience Mr Mrs Ms Miss Doctor Dr Chief Executive
Officer Managing Director General Manager Head Lead Senior Junior Associate Owner Founder President Partner Principal
Assistant Sales Operations Office Marketing Account Executive Coordinator Specialist Administrator Supervisor Chef Pastry
Sous Front Desk Technician Stylist Hygienist Receptionist Attorney Agent Broker Realtor Coach Trainer Instructor Therapist
Designer Developer Engineer Consultant Advisor Accountant Bookkeeper Nurse Practitioner Physician Assistant Dentist
Orthodontist Veterinarian Chiropractor Doctor Esq Jr Sr II III DDS DMD MD DVM DC CPA PhD RN Co Vice VP Customer Client
Happy Hour Gift Card Cards Order Delivery Pickup Catering Private Events Event Wedding Weddings Party Parties Holiday
For And Is Has Have Had With From In At To Of On By As Was Were Will Can Our Their His Her This That These Those Also Who
Quick Answers Answer Links Link Frequently Asked Questions Question Cosmetic Restorative General Pediatric Preventive Emergency
Dentistry Orthodontics Implants Implant Whitening Veneers Crowns Cleanings Cleaning Exams Smile Smiles Teeth Patient Patients
Master Plumber Plumbers Electrician Electricians Educator Educators Haircutting Haircut Haircuts Color Colorist Colour Cut Cuts
Technicians Financing Wisetack Water Heater Heaters Drain Drains Sewer Leak Leaks Repairs Installation Installations Replacement
Residential Commercial Maintenance Inspection Inspections Same Day Hour Hours Fast Reliable Trusted Affordable Certified
Learn Explore Discover Start Started Let Lets Talk Text Message Chat Visit Stop Come Love Loved Thanks Thank Hello Hi Hey
Austin Texas Dallas Houston Round Rock Cedar Park Georgetown Pflugerville City County Area Areas Near Me
Meet Staff People Leadership Careers Career Jobs Job Apply Hiring Join Policy Accessibility Statement Sitemap Cookie Cookies
Friend Friends Referral Referrals Program Programs Missing One Two Three Rewards Reward Loyalty Insider
Specials Special Offers Offer Coupons Coupon Deals Deal Discount Membership Plan Plans Pricing Price Prices Cost Payment Payments'''.split())
OWNER_RANK_CUTOFF = 13  # owner .. md in ROLE_RANK

PATTERNS = [
    re.compile(rf"\b(?:founded|owned(?: and operated)?|run|led|started|established)\s+(?:in\s+\d{{4}}\s+)?by\s+(?:Dr\.\s+)?({NAME})"),
    re.compile(rf"\b(?:I'm|I am|My name is|Hi,? I'm|Hello,? I'm)\s+(?:Dr\.\s+)?({NAME})"),
    re.compile(rf"\b(Dr\.\s+{NAME})"),
    re.compile(rf"\b({NAME})\s*(?:,|–|—|-|\||:|\bis\b(?: the)?|\bour\b)?\s*(?:our\s+|the\s+)?({ROLE_WORDS})\b"),
    re.compile(rf"\b({ROLE_WORDS})\s*(?:&\s*\w+\s*)?(?:,|:|–|—|-|\|)\s*(?:Dr\.\s+)?({NAME})"),
]
ROLE_RANK = ['owner', 'founder', 'proprietor', 'ceo', 'president', 'principal', 'managing', 'partner', 'broker', 'dds', 'dmd',
             'dr.', 'md', 'director', 'chef', 'manager', 'dentist', 'attorney']


def _valid_name(n: str) -> bool:
    is_dr = n.startswith('Dr. ')
    toks = n.replace('Dr. ', '').split()
    if not (1 if is_dr else 2) <= len(toks) <= 4:
        return False
    if any(t.strip('.') in STOP for t in toks):
        return False
    return all(len(t.strip('.')) >= 1 for t in toks)


def _role_rank(t: str | None) -> int:
    t = (t or '').lower()
    for i, k in enumerate(ROLE_RANK):
        if k in t:
            return i
    return len(ROLE_RANK)


def extract_people(soup: BeautifulSoup, html: str, page_url: str) -> list[dict[str, Any]]:
    people: dict[str, dict[str, Any]] = {}

    def add(name: str, title: str | None, src: str) -> None:
        name = re.sub(r'\([^)]*\)', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip(' ,.-')
        toks = name.split()
        while len(toks) > (2 if toks and toks[0] == 'Dr.' else 1) and toks[-1].strip('.') in STOP:
            toks.pop()
        name = ' '.join(toks)
        if not _valid_name(name):
            return
        cur = people.get(name)
        if cur is None or (_role_rank(title) < _role_rank(cur.get('title'))):
            people[name] = {'name': name, 'title': (title or None) and title.strip()[:60], 'source': src}

    # JSON-LD
    for s in soup.find_all('script', type=re.compile('ld\\+json', re.I)):
        try:
            data = json.loads(s.string or '')
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack.extend(d)
                continue
            if not isinstance(d, dict):
                continue
            if '@graph' in d:
                stack.extend(d['@graph'] if isinstance(d['@graph'], list) else [d['@graph']])
            for key, role in (('founder', 'Founder'), ('employee', None), ('founders', 'Founder'), ('author', None)):
                v = d.get(key)
                for p in (v if isinstance(v, list) else [v]):
                    if isinstance(p, dict) and isinstance(p.get('name'), str):
                        add(p['name'], p.get('jobTitle') or role, page_url)
                    elif isinstance(p, str) and key != 'author':
                        add(p, role, page_url)
            if d.get('@type') == 'Person' and isinstance(d.get('name'), str):
                add(d['name'], d.get('jobTitle'), page_url)

    # Headings / bold followed by a role line (team cards)
    for el in soup.find_all(['h2', 'h3', 'h4', 'h5', 'strong', 'b']):
        raw_t = el.get_text(' ', strip=True)
        t = re.sub(r'\s*\([^)]*\)\s*', ' ', raw_t).strip()
        if not (5 <= len(t) <= 40) or not re.fullmatch(rf'(?:Dr\.\s+)?{NAME}(?:,\s*[A-Z]{{2,4}})?', t):
            continue
        nxt = el.find_next(string=True)
        sib_text = ''
        n = el
        seen_txt = 0
        for _ in range(40):
            n = n.find_next(string=True) if n else None
            if n is None or seen_txt >= 4:
                break
            st = n.strip()
            if not st or n.parent.name in ('script', 'style'):
                continue
            seen_txt += 1
            if st and st not in raw_t and not re.fullmatch(r'\(?[a-z]+/[a-z]+\)?', st):
                sib_text = st
                break
        short = sib_text if len(sib_text) <= 50 else ''
        ms = re.search(ROLE_WORDS, short, re.I)
        m = ms or re.search(ROLE_WORDS, t)
        if m and nxt is not None:
            add(re.sub(r',\s*[A-Z]{2,4}$', '', t), short if ms else m.group(0), page_url)

    text = soup.get_text(' ', strip=True)[:150000]
    for i, rx in enumerate(PATTERNS):
        for m in rx.finditer(text):
            if i == 0:
                add(m.group(1), 'Founder/Owner', page_url)
            elif i == 1:
                add(m.group(1), None, page_url)
            elif i == 2:
                add(m.group(1), 'Dr.', page_url)
            elif i == 3:
                add(m.group(1), m.group(2), page_url)
            else:
                add(m.group(2), m.group(1), page_url)
            if len(people) > 25:
                break
    return sorted(people.values(), key=lambda p: _role_rank(p.get('title')))[:10]


def _person_key(name: str) -> str:
    toks = [t for t in name.replace('Dr. ', '').split() if not re.fullmatch(r'[A-Z]\.', t)]
    return (toks[0] + ' ' + toks[-1]).lower() if len(toks) > 1 else 'dr ' + toks[0].lower()


def merge_people(people: list[dict[str, Any]], business_name: str | None = None, domain: str | None = None) -> list[dict[str, Any]]:
    """Dedupe people across pages (Dr. X Y == X Y), drop names that are just the business name."""
    biz = set(re.findall(r'[a-z]+', (business_name or '').lower())) | set(re.findall(r'[a-z]{3,}', (domain or '').split('.')[0].lower()))
    dom = (domain or '').split('.')[0].lower()
    merged: dict[str, dict[str, Any]] = {}
    for p in people:
        toks = [t.lower().strip('.') for t in p['name'].replace('Dr. ', '').split() if len(t.strip('.')) > 1]
        if toks and all(t in biz or (len(toks) > 1 and t in dom and len(t) > 3 and toks[0] in dom) for t in toks):
            continue
        k = _person_key(p['name'])
        cur = merged.get(k)
        if cur is None:
            merged[k] = dict(p)
            continue
        better_title = _role_rank(p.get('title')) < _role_rank(cur.get('title'))
        if better_title:
            cur['title'] = p.get('title')
            cur['source'] = p.get('source')
        # prefer the fuller display name (with Dr./middle initial)
        if len(p['name']) > len(cur['name']) and len(p['name'].split()) <= 4:
            cur['name'] = p['name']
    # single-token "Dr. X" merged into a full "Dr. X Y" with the same last name
    full = {_person_key(p['name']).split()[-1]: k for k, p in merged.items() if not k.startswith('dr ')}
    for k in [k for k in merged if k.startswith('dr ')]:
        last = k.split()[-1]
        if last in full:
            tgt = merged[full[last]]
            if _role_rank(merged[k].get('title')) < _role_rank(tgt.get('title')):
                tgt['title'] = merged[k].get('title')
            del merged[k]
    return sorted(merged.values(), key=lambda p: _role_rank(p.get('title')))[:10]


LOW_PRIORITY_LOCAL = {'careers', 'career', 'jobs', 'job', 'hr', 'hiring', 'recruiting', 'press', 'media', 'pr', 'billing',
                      'accounts', 'accounting', 'invoices', 'privacy', 'legal', 'webmaster', 'noreply', 'no-reply', 'marketing'}


def email_priority(e: str) -> int:
    local = e.split('@')[0].lower()
    return 1 if local in LOW_PRIORITY_LOCAL else 0


# ---------------------------------------------------------------- page checks

def site_name(soup: BeautifulSoup, domain: str | None = None) -> str | None:
    m = soup.find('meta', attrs={'property': 'og:site_name'})
    if m and (m.get('content') or '').strip():
        return m['content'].strip()[:100]
    t = soup.title.get_text(' ', strip=True) if soup.title else ''
    if not t:
        return None
    parts = [p.strip() for p in re.split(r'\s[|–—\-:·•]\s', t) if p.strip()]
    if not parts:
        return None
    if len(parts) > 1 and parts[0].lower() in ('home', 'homepage', 'welcome', 'official site', 'official website'):
        parts = parts[1:]
    if len(parts) > 1 and domain:
        stem = re.sub(r'[^a-z0-9]', '', domain.split('.')[0].lower().replace('www', ''))
        for p in parts:
            words = [w for w in re.findall(r'[a-z0-9]+', p.lower()) if len(w) > 2]
            if words and any(w in stem for w in words):
                return p[:100]
    return min(parts, key=len)[:100] if len(parts) > 1 else parts[0][:100]

def find_subpages(soup: BeautifulSoup, base_url: str, limit: int = 3) -> list[str]:
    base_dom = domain_of(base_url)
    scored: list[tuple[int, str]] = []
    keys = [('about', 3), ('team', 3), ('our-story', 3), ('meet', 3), ('staff', 2), ('who-we-are', 3), ('leadership', 2),
            ('people', 1), ('founder', 3), ('owner', 3), ('doctor', 2), ('providers', 1), ('attorneys', 2), ('contact', 2)]
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            continue
        u = urljoin(base_url, href).split('#')[0]
        if domain_of(u) != base_dom or re.search(r'\.(pdf|jpe?g|png|gif|zip|docx?|vcf)$', u, re.I):
            continue
        if '?' in u or re.search(r'/(wp-admin|wp-json|cart|checkout|account|login)\b|career|jobs|join-our-team|hiring|employment', u, re.I):
            continue
        txt = (a.get_text(' ', strip=True) + ' ' + urlparse(u).path).lower()
        s = max((w for k, w in keys if k in txt), default=0)
        if s:
            scored.append((s, u))
    out: list[str] = []
    contact_taken = False
    for s, u in sorted(scored, key=lambda x: -x[0]):
        if u.rstrip('/') == base_url.rstrip('/') or u in out:
            continue
        is_contact = 'contact' in u.lower()
        if is_contact and contact_taken:
            continue
        contact_taken = contact_taken or is_contact
        out.append(u)
        if len(out) >= limit:
            break
    return out


_COPY_RX = re.compile(_lower_pattern(r'(?:©|&copy;|&#169;|\(c\)|copyright)[^0-9<]{0,40}((?:19|20)\d{2})(?:\s*(?:-|\u2013|\u2014|&ndash;|&mdash;|to)\s*((?:19|20)\d{2}))?'))
_DYN_YEAR_RX = re.compile(_lower_pattern(r'(?:©|&copy;|copyright)[^<]{0,60}(?:new Date\(\)\.getFullYear|document\.write|\{\{\s*year|\[year\])'))

# Click-to-call link (tel:) and on-site reviews or testimonials. Cheap substring and regex checks on the homepage.
_TEL_RX = re.compile(r'href\s*=\s*["\']?\s*tel:')
REVIEW_WIDGETS = ['elfsight', 'trustindex', 'birdeye', 'podium.com', 'nicejob', 'grade.us', 'reviewsonmywebsite', 'embedsocial',
                  'sociablekit', 'repuso', 'trustpilot', 'yotpo', 'judge.me', 'reviewwave', 'broadly.com', 'widewail',
                  'gatherup', 'getfivestars', 'reviews.io', 'shapo.io', 'senja.io', 'google-reviews', 'wprevpro', 'wp-google-reviews',
                  'richplugins', 'grw-', 'ti-widget', 'yelp.com/biz', 'homeadvisor.com/rated', 'angi.com/companylist']
_REVIEW_RX = re.compile(r'>\s*(?:(?:customer |client |google |our )?reviews|read (?:our |more )?reviews|what (?:our )?(?:customers|clients|neighbors|homeowners) (?:are saying|say))\s*<'
                        r'|href\s*=\s*["\'][^"\']*/(?:reviews?|testimonials?)[/"\'?#]')


def has_contact_form(hl: str, soup: BeautifulSoup) -> bool:
    """hl = lower-cased html. Same rule page_checks uses; cheap enough to run on subpages."""
    if any(t in hl for t in FORM_TOOLS):
        return True
    for f in soup.find_all('form'):
        if f.find('textarea') or f.find('input', attrs={'type': 'email'}) or f.find('input', attrs={'name': re.compile('email|phone|message', re.I)}):
            if 'search' not in (f.get('role') or '') + ' '.join(f.get('class') or []) + (f.get('action') or ''):
                return True
    return False


def page_checks(html: str, soup: BeautifulSoup) -> dict[str, Any]:
    hl = html.lower()
    title = (soup.title.get_text(strip=True) if soup.title else '') or ''
    md = soup.find('meta', attrs={'name': re.compile('^description$', re.I)})
    meta_desc = (md.get('content') or '').strip() if md else ''
    viewport = bool(soup.find('meta', attrs={'name': re.compile('^viewport$', re.I)}))
    h1 = soup.find('h1')
    years: list[int] = []
    for m in _COPY_RX.finditer(hl):
        for g in m.groups():
            if g and 1995 <= int(g) <= YEAR + 1:
                years.append(int(g))
    dynamic_year = bool(_DYN_YEAR_RX.search(hl))
    analytics = _detect(hl, ANALYTICS, regex=True)
    ad_pixels = _detect(hl, AD_PIXELS, regex=True)
    booking = _detect(hl, BOOKING)
    if not booking and re.search(r'>\s*(?:book (?:now|online|an? appointment)|schedule (?:now|online|an? appointment)|request an? appointment|make a reservation|reserve a table)\s*<', hl):
        booking = ['Booking link/button']
    chat = _detect(hl, CHAT)
    has_form = has_contact_form(hl, soup)
    builder, generator = detect_builder(html, hl)
    schema_types: list[str] = []
    for s in soup.find_all('script', type=re.compile('ld\\+json', re.I)):
        schema_types += re.findall(r'"@type"\s*:\s*"([A-Za-z]+)"', s.string or '')
    local_types = {'LocalBusiness', 'Organization', 'Restaurant', 'Dentist', 'MedicalBusiness', 'ProfessionalService',
                   'HomeAndConstructionBusiness', 'Plumber', 'Electrician', 'HVACBusiness', 'RoofingContractor', 'LegalService',
                   'Attorney', 'AutoRepair', 'BeautySalon', 'HairSalon', 'DaySpa', 'HealthAndBeautyBusiness', 'Store',
                   'FoodEstablishment', 'Physician', 'MedicalClinic', 'RealEstateAgent', 'AccountingService', 'VeterinaryCare',
                   'ExerciseGym', 'SportsActivityLocation', 'LodgingBusiness', 'Hotel', 'CafeOrCoffeeShop', 'Bakery',
                   'Locksmith', 'MovingCompany', 'GeneralContractor', 'HousePainter', 'ChildCare', 'Corporation', 'NailSalon'}
    has_tel = bool(_TEL_RX.search(hl))
    has_reviews = (any(t in hl for t in REVIEW_WIDGETS) or 'testimonial' in hl or bool(_REVIEW_RX.search(hl))
                   or 'AggregateRating' in schema_types or 'Review' in schema_types)
    return {
        'hasClickToCall': has_tel, 'hasReviewsOnSite': has_reviews,
        'title': title[:200] or None, 'titleLength': len(title), 'metaDescription': meta_desc[:300] or None,
        'mobileViewport': viewport, 'hasH1': bool(h1 and h1.get_text(strip=True)),
        'copyrightYear': max(years) if years else None, 'copyrightDynamic': dynamic_year,
        'analytics': analytics, 'adPixels': ad_pixels, 'bookingTools': booking, 'chatWidgets': chat,
        'hasContactForm': has_form, 'builder': builder, 'generator': generator,
        'structuredData': sorted(set(schema_types))[:15],
        'hasLocalBusinessSchema': bool(set(schema_types) & local_types),
        'flashOrLegacy': bool(re.search(r'\.swf\b|<frameset|<marquee|<font\s', hl)),
        'imagesCount': len(soup.find_all('img')), 'scriptsCount': len(soup.find_all('script')),
    }


# ---------------------------------------------------------------- scoring

ISSUE_TEXT = {
    'NO_WEBSITE': 'No website listed',
    'SITE_DOWN': 'Website does not load',
    'SITE_ERROR': 'Website returns an error page',
    'NO_HTTPS': 'No HTTPS ("Not secure" warning in browsers)',
    'INVALID_SSL': 'Invalid or expired SSL certificate',
    'NO_HTTPS_REDIRECT': 'HTTP version does not redirect to HTTPS',
    'NOT_MOBILE_FRIENDLY': 'No mobile viewport (not set up for phones)',
    'VERY_SLOW': 'Very slow homepage (over 5 s)',
    'SLOW': 'Slow homepage (over 2.5 s)',
    'HEAVY_PAGE': 'Heavy homepage HTML (over 1.5 MB)',
    'MISSING_TITLE': 'Missing or very short page title',
    'MISSING_META_DESCRIPTION': 'Missing meta description',
    'NO_H1': 'No H1 heading',
    'OUTDATED_COPYRIGHT': 'Outdated copyright year in footer',
    'NO_ANALYTICS': 'No Google Analytics or Tag Manager',
    'NO_AD_PIXEL': 'No ad tracking pixel (Meta, TikTok, Google Ads)',
    'NO_LEAD_CAPTURE': 'No online booking, contact form or chat',
    'NO_BOOKING': 'No online booking',
    'NO_LOCAL_SCHEMA': 'No LocalBusiness structured data',
    'NO_SOCIAL_LINKS': 'No social media links',
    'LEGACY_TECH': 'Legacy markup (frames, Flash or <font> tags)',
    'NO_EMAIL_ON_SITE': 'No email address on the website',
    'LOW_RATING': 'Low Google rating',
    'FEW_REVIEWS': 'Few Google reviews',
    'NO_CLICK_TO_CALL': 'No click-to-call phone link on the homepage',
    'NO_REVIEWS_ON_SITE': 'No reviews or testimonials shown on the homepage',
}
# Points per issue (scoring version 2, calibrated 2026-11-14 on 165 real Google LSA advertiser websites).
# The score is the sum of points for the issues found, capped at 100. Weights reflect how much each gap costs a local
# business in leads: broken or insecure sites first, then ways to convert a visitor (form, booking, click-to-call),
# then measurement, speed and search basics, then trust signals. Small nice-to-haves stay at a few points.
POINTS = {'NO_WEBSITE': 100, 'SITE_DOWN': 100, 'SITE_ERROR': 85,
          'NO_HTTPS': 30, 'INVALID_SSL': 30, 'NOT_MOBILE_FRIENDLY': 25, 'NO_LEAD_CAPTURE': 25, 'VERY_SLOW': 20,
          'NO_ANALYTICS': 12, 'LEGACY_TECH': 12, 'LOW_RATING': 12, 'SLOW': 10, 'MISSING_TITLE': 10, 'OUTDATED_COPYRIGHT': 10,
          'NO_CLICK_TO_CALL': 10, 'NO_HTTPS_REDIRECT': 8, 'MISSING_META_DESCRIPTION': 8, 'NO_LOCAL_SCHEMA': 8, 'FEW_REVIEWS': 8,
          'NO_BOOKING': 6, 'NO_AD_PIXEL': 6, 'NO_H1': 6, 'NO_REVIEWS_ON_SITE': 6, 'HEAVY_PAGE': 5,
          'NO_EMAIL_ON_SITE': 4, 'NO_SOCIAL_LINKS': 4}
SEVERITY = {p: ('high' if v >= 20 else 'medium' if v >= 8 else 'low') for p, v in POINTS.items()}
# Grade bands on the 0-100 problem score. A = at most one 4-point gap; F = a broken, insecure or lead-losing site.
GRADE_BANDS = [(4, 'A'), (14, 'B'), (26, 'C'), (38, 'D')]
SCORING_VERSION = 2
SLOW_MS, VERY_SLOW_MS = 2500, 5000


def collect_issues(c: dict[str, Any], rating: float | None, reviews: int | None, status: str) -> list[str]:
    issues: list[str] = []
    if status == 'noWebsite':
        issues.append('NO_WEBSITE')
    elif status == 'down':
        issues.append('SITE_DOWN')
    elif status == 'httpError':
        issues.append('SITE_ERROR')
    else:
        if c.get('sslInvalid'):
            issues.append('INVALID_SSL')
        elif not c.get('https'):
            issues.append('NO_HTTPS')
        elif c.get('httpRedirectsToHttps') is False:
            issues.append('NO_HTTPS_REDIRECT')
        if not c.get('mobileViewport'):
            issues.append('NOT_MOBILE_FRIENDLY')
        rt = c.get('responseTimeMs') or 0
        if rt > VERY_SLOW_MS:
            issues.append('VERY_SLOW')
        elif rt > SLOW_MS:
            issues.append('SLOW')
        if (c.get('pageSizeKb') or 0) > 1500:
            issues.append('HEAVY_PAGE')
        if (c.get('titleLength') or 0) < 10:
            issues.append('MISSING_TITLE')
        if not c.get('metaDescription'):
            issues.append('MISSING_META_DESCRIPTION')
        if not c.get('hasH1'):
            issues.append('NO_H1')
        cy = c.get('copyrightYear')
        if cy and cy <= YEAR - 2 and not c.get('copyrightDynamic'):
            issues.append('OUTDATED_COPYRIGHT')
        if not c.get('analytics'):
            issues.append('NO_ANALYTICS')
        if not c.get('adPixels'):
            issues.append('NO_AD_PIXEL')
        if not c.get('bookingTools') and not c.get('hasContactForm') and not c.get('chatWidgets'):
            issues.append('NO_LEAD_CAPTURE')
        elif not c.get('bookingTools'):
            issues.append('NO_BOOKING')
        # Checks added in scoring version 2. Missing keys (older saved rows) are treated as passed.
        if c.get('hasClickToCall') is False:
            issues.append('NO_CLICK_TO_CALL')
        if c.get('hasReviewsOnSite') is False:
            issues.append('NO_REVIEWS_ON_SITE')
        if not c.get('hasLocalBusinessSchema'):
            issues.append('NO_LOCAL_SCHEMA')
        if not c.get('hasSocialLinks'):
            issues.append('NO_SOCIAL_LINKS')
        if c.get('flashOrLegacy'):
            issues.append('LEGACY_TECH')
        if not c.get('hasEmail'):
            issues.append('NO_EMAIL_ON_SITE')
    if rating is not None and 0 < rating < 4.0:
        issues.append('LOW_RATING')
    if reviews is not None and reviews < 20:
        issues.append('FEW_REVIEWS')
    return issues


def score_to_grade(s: int) -> str:
    return next((g for top, g in GRADE_BANDS if s <= top), 'F')


def score(issues: list[str]) -> tuple[int, str]:
    s = min(100, sum(POINTS[i] for i in issues))
    return s, score_to_grade(s)


# ---------------------------------------------------------------- pitch

PITCH_ORDER = ['NO_WEBSITE', 'SITE_DOWN', 'SITE_ERROR', 'INVALID_SSL', 'NO_HTTPS', 'NOT_MOBILE_FRIENDLY', 'VERY_SLOW',
               'NO_LEAD_CAPTURE', 'LOW_RATING', 'OUTDATED_COPYRIGHT', 'LEGACY_TECH', 'SLOW', 'NO_CLICK_TO_CALL', 'FEW_REVIEWS',
               'NO_ANALYTICS', 'MISSING_META_DESCRIPTION', 'MISSING_TITLE', 'NO_REVIEWS_ON_SITE', 'NO_BOOKING', 'NO_AD_PIXEL',
               'NO_LOCAL_SCHEMA', 'NO_HTTPS_REDIRECT']


def first_name(full: str | None) -> str | None:
    if not full:
        return None
    toks = full.replace('Dr. ', '').split()
    return toks[0] if toks else None


def pitch(issues: list[str], ctx: dict[str, Any]) -> tuple[str, str, str | None]:
    """Returns (pitchAngle, emailOpener, primaryIssue)."""
    biz = ctx.get('businessName') or ctx.get('domain') or 'your business'
    if not ctx.get('businessName') and not ctx.get('domain'):
        biz = 'your business'
    dom = ctx.get('domain') or 'your website'
    cat = (ctx.get('category') or 'business').lower()
    city = ctx.get('city')
    where = f' in {city}' if city else ''
    owner = ctx.get('ownerName') or ''
    hi = f'Hi Dr. {owner.split()[-1]}' if owner.startswith('Dr.') else (f'Hi {first_name(owner)}' if owner else 'Hi there')
    rating, reviews = ctx.get('rating'), ctx.get('reviewCount')
    secs = round((ctx.get('responseTimeMs') or 0) / 1000, 1)
    cy = ctx.get('copyrightYear')
    primary = next((i for i in PITCH_ORDER if i in issues), None)
    t = {
        'NO_WEBSITE': (f'No own website (only a listing or social page): people searching for a {cat}{where} have nowhere to book or learn more. Pitch a simple site with booking.',
                       f"{hi}, I came across {biz}{' on Google Maps' if ctx.get('source') == 'googleMaps' else ''}{f' ({rating}★)' if rating else ''} but couldn't find a website, so anyone searching for a {cat}{where} has nowhere to click through to."),
        'SITE_DOWN': (f'{dom} does not load, so visitors from Google and Maps hit a dead end. Pitch an urgent fix or rebuild.',
                      f"{hi}, I tried to visit {dom} today and it wouldn't load. You may be losing visitors from Google right now."),
        'SITE_ERROR': (f'{dom} returns an error page. Pitch an urgent fix.',
                       f"{hi}, I opened {dom} today and got an error page instead of your homepage. Thought you'd want to know."),
        'INVALID_SSL': (f'{dom} has an invalid SSL certificate, so browsers show a security warning before the page opens. Pitch a fix and maintenance plan.',
                        f"{hi}, when I opened {dom}, Chrome showed a security warning before the page loaded. That scares off a lot of visitors."),
        'NO_HTTPS': (f'{dom} has no HTTPS, so Chrome labels it "Not secure". Pitch SSL plus a refresh.',
                     f"{hi}, I noticed {dom} shows a \"Not secure\" label in Chrome, which can put visitors off before they call."),
        'NOT_MOBILE_FRIENDLY': (f'{dom} is not set up for phones (no mobile viewport). Most local searches happen on mobile. Pitch a mobile-first redesign.',
                                f"{hi}, I looked at {dom} on my phone and it isn't set up for mobile. Most people searching for a {cat}{where} are on their phones."),
        'VERY_SLOW': (f'{dom} took {secs}s to load. Pitch speed optimisation or rebuild.',
                      f"{hi}, {dom} took about {secs} seconds to load for me. Most visitors give up after about three."),
        'SLOW': (f'{dom} took {secs}s to load. Pitch speed optimisation.',
                 f"{hi}, {dom} took about {secs} seconds to load for me. Shaving that down usually means more calls from the same traffic."),
        'NO_LEAD_CAPTURE': (f'No online booking, contact form or chat on {dom}, so visitors who don\'t want to call just leave. Pitch a booking or lead form.',
                            f"{hi}, I couldn't find a way to book or send a request on {dom}. Visitors who don't want to phone have no way to reach you."),
        'LOW_RATING': (f'{biz} has a {rating}★ Google rating from {reviews} reviews. Pitch review generation and reputation management.',
                       f"{hi}, I saw {biz} has a {rating}★ rating on Google. A steady stream of fresh reviews would help you stand out from other {cat}s{where}."),
        'FEW_REVIEWS': (f'Only {reviews} Google reviews. Pitch a review-generation system.',
                        f"{hi}, {biz} only has {reviews} Google reviews, so competitors with more reviews tend to get picked first{where}."),
        'OUTDATED_COPYRIGHT': (f'Footer still says © {cy}, so the site looks unmaintained. Pitch a refresh and a care plan.',
                               f"{hi}, the footer on {dom} still says © {cy}, which can make the site look unmaintained to new customers."),
        'LEGACY_TECH': (f'{dom} uses legacy markup. Pitch a modern rebuild.',
                        f"{hi}, {dom} is built with some quite old web technology, which tends to hurt both Google rankings and mobile visitors."),
        'NO_ANALYTICS': (f'No Google Analytics or Tag Manager on {dom}, so there is no visibility into where customers come from. Pitch tracking and reporting.',
                         f"{hi}, I noticed {dom} has no analytics installed, so there's no easy way to see which marketing is actually bringing in customers."),
        'MISSING_META_DESCRIPTION': (f'{dom} has no meta description, so Google writes its own snippet. Pitch local SEO basics.',
                                     f"{hi}, {dom}'s homepage has no meta description, so Google picks a random snippet when it shows you in search results."),
        'MISSING_TITLE': (f'{dom} has no proper page title. Pitch local SEO basics.',
                          f"{hi}, {dom}'s homepage is missing a proper page title, which is one of the first things Google uses to rank a {cat}{where}."),
        'NO_CLICK_TO_CALL': (f'{dom} has no tap-to-call phone link, so mobile visitors have to copy the number by hand. Pitch a mobile conversion fix.',
                             f"{hi}, on my phone there was no tap-to-call button on {dom}, so calling you takes a few extra steps most visitors won't bother with."),
        'NO_REVIEWS_ON_SITE': (f'{dom} shows no reviews or testimonials on the homepage. Pitch a reviews widget and social proof.',
                               f"{hi}, {dom} doesn't show any customer reviews or testimonials, and that is often where new visitors decide whether to call."),
        'NO_BOOKING': (f'{dom} has no online booking. Pitch booking integration.',
                       f"{hi}, I noticed there's no way to book online on {dom}. Many customers now expect to grab a slot without calling."),
        'NO_AD_PIXEL': (f'No ad pixel on {dom}, so no retargeting or conversion tracking. Pitch paid ads setup.',
                        f"{hi}, {dom} has no ad tracking pixel installed, so anyone who visits and leaves can't be reached again with ads."),
        'NO_LOCAL_SCHEMA': (f'No LocalBusiness structured data on {dom}. Pitch local SEO and AI-search readiness.',
                            f"{hi}, {dom} is missing the structured business data Google and AI assistants use to recommend a {cat}{where}."),
        'NO_HTTPS_REDIRECT': (f'http://{dom} does not redirect to HTTPS. Pitch a technical cleanup.',
                              f"{hi}, the non-secure http:// version of {dom} still loads without redirecting, which can split your Google rankings."),
    }
    if primary:
        a, o = t[primary]
        return a, o, primary
    return (f'{dom} is in good shape technically. Pitch growth: SEO content, ads or reviews.',
            f"{hi}, {dom} looks well put together. I had a couple of ideas to bring more {cat} customers{where} through it.", None)
