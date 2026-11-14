from __future__ import annotations

import asyncio
import random
import re
import ssl
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from apify import Actor
from bs4 import BeautifulSoup

from . import audit as A

STATE_STORE = 'local-lead-audit-state'
EV_AUDIT = 'lead-audit'
EV_CONTACT = 'contact-found'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
MAX_BYTES = 3_000_000
SITE_TIMEOUT_SECS = 60      # hard cap per business (homepage + subpages + MX)
STOP_NEW_BEFORE_SECS = 60   # stop starting new sites this long before the run timeout
HARD_STOP_BEFORE_SECS = 30  # cancel in-flight sites and save results this long before the run timeout (exit needs ~10 s at 256 MB)
ST_TIME = 'skippedTimeLimit'
BLOCK_MARKERS = ('cf-chl', 'challenge-platform', 'just a moment...', 'attention required! | cloudflare', 'cf-browser-verification',
                 '_incapsula_resource', 'incapsula incident', 'datadome', 'sgcaptcha', 'perimeterx', 'px-captcha',
                 'access denied</title>', 'request unsuccessful. incapsula', 'please verify you are a human',
                 'ddos protection by', 'checking your browser', 'captcha-delivery', 'are you a robot',
                 '<title>human verification', 'awswafcookiedomainlist', 'gokuprops', 'sucuri website firewall',
                 'wordfence', 'access to this page has been denied', 'bot protection', 'hcaptcha.com/1/api.js',
                 'g-recaptcha" data-sitekey', 'imunify360', 'blocked by', 'you have been blocked')


def make_soup(html: str) -> BeautifulSoup:
    # Measured: stripping script/style bodies with a regex first costs more CPU than it saves, so parse as is.
    return BeautifulSoup(html, 'lxml')


def _list(v: Any) -> list[str]:
    if isinstance(v, str):
        v = re.split(r'[\n,]', v)
    return [x.strip() for x in (v or []) if isinstance(x, str) and x.strip()]


def state_key(k: str) -> str:
    return re.sub(r"[^a-zA-Z0-9!\-_.'()]", '-', k.strip())[:200] or 'default'


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def dataset_id_from(v: str) -> str:
    v = (v or '').strip()
    m = re.search(r'datasets/([A-Za-z0-9]{8,})', v)
    return m.group(1) if m else v


def _num(v: Any) -> float | None:
    try:
        return float(v) if v is not None and v != '' else None
    except (TypeError, ValueError):
        return None


def lead_from_maps(it: dict[str, Any]) -> dict[str, Any]:
    reviews = _num(next((it.get(k) for k in ('reviewsCount', 'reviewCount', 'reviews', 'user_ratings_total') if isinstance(it.get(k), (int, float, str))), None))
    return {
        'source': 'googleMaps',
        'businessName': it.get('title') or it.get('name'),
        'inputWebsite': it.get('website') or it.get('url_website') or it.get('site') or it.get('domain') or None,
        'category': it.get('categoryName') or ((it.get('categories') or [None])[0] if isinstance(it.get('categories'), list) else None),
        'city': it.get('city'), 'address': it.get('address'),
        'mapsPhone': it.get('phone') or it.get('phoneUnformatted'),
        'rating': _num(it.get('totalScore') if it.get('totalScore') is not None else it.get('rating')),
        'reviewCount': int(reviews) if reviews is not None else None,
        'mapsUrl': it.get('url') if 'google.' in str(it.get('url') or '') else None,
        'placeId': it.get('placeId'),
        'mapsEmails': [e for e in (it.get('emails') or []) if isinstance(e, str)],
        'permanentlyClosed': bool(it.get('permanentlyClosed')),
    }


def timed_get_sync(url: str, verify: bool) -> int | None:
    """Re-times one homepage download in a worker thread. HTML parsing is CPU bound and blocks the event loop, so an
    asyncio timer under load also counts time spent parsing other sites. A blocking read in a thread is woken within a
    few ms (the GIL switch interval), so this measures the website, not how busy the run is. Used only to confirm a
    homepage that looked slow."""
    try:
        with httpx.Client(headers={'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml'}, verify=verify,
                          follow_redirects=True, timeout=httpx.Timeout(12.0, connect=6.0)) as c:
            t0 = time.monotonic()
            with c.stream('GET', url) as r:
                n = 0
                for chunk in r.iter_bytes():
                    n += len(chunk)
                    if n > MAX_BYTES:
                        break
            return int((time.monotonic() - t0) * 1000)
    except Exception:
        return None


class Fetcher:
    """Plain HTTP. Datacenter proxy only as a fallback for blocked sites on the platform (or if set in input)."""

    def __init__(self, proxy_input: dict | None, allow_fallback: bool, concurrency: int):
        self.proxy_input = proxy_input or {}
        self.allow_fallback = allow_fallback
        lim = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
        self.lim = lim
        self.client = self._mk(None, True)
        self.insecure = self._mk(None, False)
        self.proxy_client: httpx.AsyncClient | None = None
        self.proxy_tried = False
        self.requests = 0
        self.proxy_requests = 0
        self.lock = asyncio.Lock()

    def _mk(self, proxy: str | None, verify: bool) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=httpx.Timeout(15, connect=8), verify=verify, follow_redirects=True,
                                 max_redirects=6, proxy=proxy, limits=self.lim, headers={
                                     'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9',
                                     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})

    async def init(self) -> None:
        if self.proxy_input.get('useApifyProxy') or self.proxy_input.get('proxyUrls'):
            cfg = await Actor.create_proxy_configuration(actor_proxy_input=self.proxy_input)
            if cfg:
                await self.client.aclose()
                self.client = self._mk(await cfg.new_url(session_id=f'l{random.randint(0, 10**9)}'), True)
                self.proxy_tried = True
                Actor.log.info('Using the proxy from input for all requests.')

    async def get_proxy_client(self) -> httpx.AsyncClient | None:
        async with self.lock:
            if self.proxy_client is None and not self.proxy_tried and self.allow_fallback and Actor.is_at_home():
                self.proxy_tried = True
                try:
                    cfg = await Actor.create_proxy_configuration()  # default = datacenter, never residential
                    if cfg:
                        self.proxy_client = self._mk(await cfg.new_url(session_id=f'f{random.randint(0, 10**9)}'), True)
                        Actor.log.info('Datacenter proxy fallback enabled for blocked sites.')
                except Exception as ex:
                    Actor.log.warning(f'Proxy fallback unavailable: {ex}')
            return self.proxy_client

    async def get(self, url: str, client: httpx.AsyncClient | None = None) -> tuple[httpx.Response, str, int]:
        c = client or self.client
        self.requests += 1
        t0 = time.monotonic()
        async with c.stream('GET', url) as r:
            buf = bytearray()
            ctype = r.headers.get('content-type', '')
            if 'html' in ctype or 'xml' in ctype or not ctype:
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > MAX_BYTES:
                        break
            elapsed = int((time.monotonic() - t0) * 1000)
            enc = r.encoding or 'utf-8'
            try:
                text = buf.decode(enc, errors='replace')
            except LookupError:
                text = buf.decode('utf-8', errors='replace')
            return r, text, elapsed

    async def head_redirect(self, url: str) -> str | None:
        try:
            self.requests += 1
            r = await self.client.get(url, follow_redirects=False, timeout=10)
            return r.headers.get('location') if 300 <= r.status_code < 400 else ''
        except Exception:
            return None

    async def close(self) -> None:
        for c in (self.client, self.insecure, self.proxy_client):
            if c:
                await c.aclose()


def is_blocked(status: int, html: str) -> bool:
    h = html[:30000].lower()
    if status in (401, 403, 429):
        return True
    if status >= 400 and any(m in h for m in BLOCK_MARKERS):
        return True
    return status < 400 and len(html) < 20000 and any(m in h for m in BLOCK_MARKERS[:9] + BLOCK_MARKERS[16:19])


def _dns_error(ex: Exception | None) -> bool:
    s = repr(ex).lower()
    return isinstance(ex, httpx.ConnectError) and ('name or service not known' in s or 'nodename nor servname' in s
                                                    or 'no address associated' in s or 'name resolution' in s)


def _ssl_error(ex: Exception) -> bool:
    s = repr(ex).lower()
    return isinstance(ex, ssl.SSLError) or 'certificate' in s or 'ssl' in s


class Output:
    def __init__(self) -> None:
        self.cm = Actor.get_charging_manager()
        self.lock = asyncio.Lock()
        self.limit_hit = False
        self.charged = Counter()
        self.pushed = 0

    async def push(self, row: dict[str, Any], chargeable: bool, contact: bool) -> bool:
        async with self.lock:
            if self.limit_hit:
                return False
            if chargeable:
                allowed = self.cm.calculate_max_event_charge_count_within_limit(EV_AUDIT)
                if allowed is not None and allowed < 1:
                    self.limit_hit = True
                    return False
                await Actor.push_data(row, charged_event_name=EV_AUDIT)
                self.charged[EV_AUDIT] += 1
                if contact:
                    allowed_c = self.cm.calculate_max_event_charge_count_within_limit(EV_CONTACT)
                    if allowed_c is None or allowed_c >= 1:
                        await Actor.charge(EV_CONTACT)
                        self.charged[EV_CONTACT] += 1
                    else:
                        self.limit_hit = True
            else:
                await Actor.push_data(row)
            self.pushed += 1
            return True


_mx_cache: dict[str, bool | None] = {}


async def mx_ok(domain: str) -> bool | None:
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        import dns.asyncresolver
        res = dns.asyncresolver.Resolver()
        res.lifetime = 5
        ans = await res.resolve(domain, 'MX')
        ok = len(ans) > 0
    except Exception as ex:
        name = type(ex).__name__
        ok = False if name in ('NXDOMAIN', 'NoAnswer', 'NoNameservers') else None
    _mx_cache[domain] = ok
    return ok


async def fetch_home(f: Fetcher, host: str, http_first: bool = False) -> dict[str, Any]:
    """Try https, fall back to insecure https (to detect bad certs), then http, then www."""
    hosts = [host] + ([f'www.{host}'] if not host.startswith('www.') and host.count('.') == 1 else [])
    last_err = None
    if http_first:
        try:
            r, html, ms = await f.get(f'http://{host}/')
            return {'resp': r, 'html': html, 'ms': ms, 'https': str(r.url).startswith('https'), 'sslInvalid': False}
        except Exception as ex:
            last_err = ex
    for h in hosts:
        try:
            r, html, ms = await f.get(f'https://{h}/')
            return {'resp': r, 'html': html, 'ms': ms, 'https': str(r.url).startswith('https'), 'sslInvalid': False}
        except Exception as ex:
            last_err = ex
            if _ssl_error(ex):
                try:
                    r, html, ms = await f.get(f'https://{h}/', f.insecure)
                    return {'resp': r, 'html': html, 'ms': ms, 'https': str(r.url).startswith('https'), 'sslInvalid': True}
                except Exception as ex2:
                    last_err = ex2
        if _dns_error(last_err):  # the host does not resolve: http:// on the same host cannot work either
            continue
        try:
            r, html, ms = await f.get(f'http://{h}/')
            return {'resp': r, 'html': html, 'ms': ms, 'https': str(r.url).startswith('https'), 'sslInvalid': False}
        except Exception as ex:
            last_err = ex
    return {'error': f'{type(last_err).__name__}: {str(last_err)[:160]}'}


async def audit_lead(f: Fetcher, lead: dict[str, Any], opts: dict[str, Any]) -> tuple[dict[str, Any], bool, bool]:
    """Returns (row, chargeable, contactFound)."""
    url = A.normalize_url(lead.get('inputWebsite') or '') if lead.get('inputWebsite') else None
    dom = A.domain_of(url) if url else None
    row: dict[str, Any] = {
        'businessName': lead.get('businessName'), 'domain': dom, 'website': None, 'inputWebsite': lead.get('inputWebsite'),
        'source': lead.get('source'), 'category': lead.get('category'), 'city': lead.get('city'), 'address': lead.get('address'),
        'rating': lead.get('rating'), 'reviewCount': lead.get('reviewCount'), 'mapsUrl': lead.get('mapsUrl'),
        'placeId': lead.get('placeId'), 'status': 'ok', 'statusDetail': None, 'httpStatus': None,
        'problemScore': None, 'grade': None, 'primaryIssue': None, 'issues': [], 'issueCodes': [], 'topIssues': None,
        'ownerName': None, 'ownerTitle': None, 'contactName': None, 'contactTitle': None, 'people': [], 'primaryEmail': None, 'emailType': None,
        'emailMxValid': None, 'emails': [], 'phones': [], 'socials': {}, 'checks': {}, 'pagesCrawled': [],
        'pitchAngle': None, 'emailOpener': None, 'auditedAt': now_iso(),
    }
    checks: dict[str, Any] = {}
    emails: list[str] = list(lead.get('mapsEmails') or [])
    phones: list[str] = [lead['mapsPhone']] if lead.get('mapsPhone') else []
    socials: dict[str, str] = {}
    people: list[dict[str, Any]] = []
    status = 'ok'

    if url and A.is_social_url(url):
        row['domain'] = None
        row['statusDetail'] = 'The listed website is a social or directory profile, not an own website.'
        socials['facebook' if 'facebook' in url else 'listed'] = url
        status = 'noWebsite'
    elif not url:
        status = 'noWebsite'
        row['statusDetail'] = 'No website on the listing.' if lead.get('source') == 'googleMaps' else 'Invalid URL.'
        if lead.get('source') != 'googleMaps':
            row['status'] = 'invalidInput'
            return row, False, False
        if not opts['includeNoWebsite']:
            row['status'] = 'skipped'
            return row, False, False
    else:
        host = urlparse(url).hostname or dom
        home = await fetch_home(f, host, http_first=str(lead.get('inputWebsite') or '').lower().startswith('http://'))
        if 'error' in home:
            status = 'down'
            row['statusDetail'] = home['error']
        else:
            r, html, ms = home['resp'], home['html'], home['ms']
            if is_blocked(r.status_code, html):
                pc = await f.get_proxy_client()
                if pc:
                    try:
                        f.proxy_requests += 1
                        r2, html2, ms2 = await f.get(str(r.url), pc)
                        if not is_blocked(r2.status_code, html2):
                            r, html, ms = r2, html2, ms2
                            checks['viaProxy'] = True
                    except Exception:
                        pass
            row['httpStatus'] = r.status_code
            final = str(r.url)
            row['website'] = final
            if is_blocked(r.status_code, html):
                row['status'] = 'blocked'
                row['statusDetail'] = f'Bot protection or access denied (HTTP {r.status_code}). Not audited, not charged.'
                return row, False, False
            fdom = A.domain_of(final)
            if fdom and fdom != dom and A.is_social_url(final):
                status = 'noWebsite'
                row['statusDetail'] = f'Website redirects to a social profile ({fdom}).'
                socials['redirect'] = final
            elif r.status_code >= 400:
                status = 'httpError'
                row['statusDetail'] = f'Homepage returned HTTP {r.status_code}.'
            else:
                if fdom and fdom != dom:
                    checks['redirectedToDomain'] = fdom
                soup = make_soup(html)
                checks.update(A.page_checks(html, soup))
                if not row['businessName']:
                    row['businessName'] = A.site_name(soup, dom)
                checks.update({'https': home['https'], 'sslInvalid': home['sslInvalid'], 'responseTimeMs': ms,
                               'pageSizeKb': round(len(html.encode('utf-8', 'ignore')) / 1024, 1)})
                if ms > A.SLOW_MS:
                    # Confirm a slow-looking homepage with a quiet re-time in a thread (see timed_get_sync).
                    checks['responseTimeFirstMs'] = ms
                    again = await asyncio.to_thread(timed_get_sync, final, not home['sslInvalid'])
                    if again is not None:
                        checks['responseTimeMs'] = min(ms, again)
                if home['https'] and not home['sslInvalid']:
                    loc = await f.head_redirect(f'http://{urlparse(final).hostname}/')
                    checks['httpRedirectsToHttps'] = None if loc is None else loc.lower().startswith('https://')
                ct = A.extract_contacts(soup, html, final)
                emails += ct['emails']
                phones += ct['phones']
                socials.update({k: v for k, v in ct['socials'].items() if k not in socials})
                people += A.extract_people(soup, html, final)
                crawled = [final]
                # Subpages are only for contacts. Skip them when the homepage already has an email on the
                # business domain, a named owner and a contact form (saves 3 requests and 3 parses per site).
                site_doms0 = {dom, fdom} - {None}
                own_email = any(e.split('@')[-1].lower().removeprefix('www.') in site_doms0 for e in emails if '@' in e)
                has_owner = any(A._role_rank(p.get('title')) < A.OWNER_RANK_CUTOFF for p in people)
                subs = A.find_subpages(soup, final, opts['maxSubpages']) if opts['maxSubpages'] > 0 else []
                # bs4 trees are reference cycles: free the homepage tree now instead of at the next GC pass,
                # before waiting on subpages. At 256 MB this keeps memory and GC work down.
                soup.decompose()
                if own_email and has_owner and checks.get('hasContactForm'):
                    checks['subpagesSkipped'] = True
                elif subs:

                    async def sub(u: str) -> None:
                        try:
                            rr, hh, _ = await f.get(u)
                            if rr.status_code >= 400 or is_blocked(rr.status_code, hh):
                                return
                            ss = make_soup(hh)
                            c2 = A.extract_contacts(ss, hh, str(rr.url))
                            emails.extend(c2['emails'])
                            phones.extend(c2['phones'])
                            for k, v in c2['socials'].items():
                                socials.setdefault(k, v)
                            people.extend(A.extract_people(ss, hh, str(rr.url)))
                            crawled.append(str(rr.url))
                            hl = hh.lower()
                            if not checks.get('hasContactForm'):
                                checks['hasContactForm'] = A.has_contact_form(hl, ss)
                            if not checks.get('bookingTools'):
                                checks['bookingTools'] = A._detect(hl, A.BOOKING)
                            ss.decompose()
                        except Exception:
                            return
                    await asyncio.gather(*(sub(u) for u in subs))
                row['pagesCrawled'] = crawled

    # contacts
    site_doms = {dom, A.domain_of(row.get('website'))} - {None}
    uniq = list(dict.fromkeys(e for e in (A.clean_email(x) for x in emails) if e))
    # prefer emails on the business domain, then personal, then generic
    uniq.sort(key=lambda e: (0 if A.domain_of('x@' + e.split('@')[1]) and e.split('@')[1].removeprefix('www.') in site_doms else 1,
                             0 if A.email_kind(e) == 'personal' else 1))
    row['emails'] = uniq[:10]
    seen: set[str] = set()
    up = []
    for p in phones:
        k = re.sub(r'\D', '', p)[-10:]
        if k and k not in seen:
            seen.add(k)
            up.append(p)
    row['phones'] = up[:6]
    row['socials'] = socials
    plist = A.merge_people(people, row.get('businessName'), row.get('domain'))
    row['people'] = plist
    if plist:
        best = plist[0]
        rank = A._role_rank(best.get('title'))
        if rank < A.OWNER_RANK_CUTOFF:
            row['ownerName'], row['ownerTitle'] = best['name'], best.get('title')
        row['contactName'], row['contactTitle'] = best['name'], best.get('title')
    # owner email match
    if row['emails']:
        row['emails'] = sorted(row['emails'], key=A.email_priority)
        pe = row['emails'][0]
        fn = (A.first_name(row['ownerName']) or '').lower()
        if fn:
            for e in row['emails']:
                if e.split('@')[0].startswith(fn) or fn in e.split('@')[0].split('.'):
                    pe = e
                    break
        row['primaryEmail'] = pe
        row['emailType'] = A.email_kind(pe)
        if opts['checkMx']:
            row['emailMxValid'] = await mx_ok(pe.split('@')[1])
    checks['hasEmail'] = bool(row['emails'])
    checks['hasSocialLinks'] = bool(socials)
    row['checks'] = checks
    row['status'] = status

    issues = A.collect_issues(checks, lead.get('rating'), lead.get('reviewCount'), status)
    s, g = A.score(issues)
    row.update({'problemScore': s, 'grade': g, 'issueCodes': issues,
                'issues': [{'code': i, 'severity': A.SEVERITY[i], 'points': A.POINTS[i], 'message': A.ISSUE_TEXT[i]} for i in issues]})
    row['topIssues'] = '; '.join(A.ISSUE_TEXT[i] for i in sorted(issues, key=lambda i: -A.POINTS[i])[:3]) or None
    if opts['includePitch']:
        ctx = {**lead, 'businessName': row['businessName'], 'domain': row['domain'], 'ownerName': row['ownerName'], 'responseTimeMs': checks.get('responseTimeMs'),
               'copyrightYear': checks.get('copyrightYear')}
        row['pitchAngle'], row['emailOpener'], row['primaryIssue'] = A.pitch(issues, ctx)
    else:
        row['primaryIssue'] = next((i for i in A.PITCH_ORDER if i in issues), None)
    site_contact = bool(row['contactName']) or any(e for e in row['emails'] if e not in (lead.get('mapsEmails') or []))
    return row, True, site_contact


def split_name_site(line: str, name: str | None = None) -> tuple[str | None, str]:
    """'Business Name | domain.com' (either order). The business name itself may contain '|', so the website is the
    last part that parses as a URL and everything else is the name."""
    parts = [x.strip() for x in line.split('|')]
    idx = next((j for j in range(len(parts) - 1, -1, -1) if ' ' not in parts[j] and A.normalize_url(parts[j])), None)
    if idx is None:
        return name, line.strip()
    rest = ' | '.join(p for k, p in enumerate(parts) if k != idx and p)
    return (rest or name), parts[idx]


async def _input_error(msg: str) -> None:
    """Fixable input problem (or an empty upstream dataset): end SUCCEEDED with one uncharged explanatory row."""
    Actor.log.error(msg)
    await Actor.push_data({'status': 'error', 'error': msg})
    await Actor.set_status_message(f'Nothing audited - {msg}'[:900], is_terminal=True)


async def main() -> None:
    async with Actor:
        inp = await Actor.get_input() or {}
        websites = _list(inp.get('websites'))
        names = _list(inp.get('businessNames'))
        ds_id = dataset_id_from(inp.get('mapsDatasetId') or '')
        if not ds_id and not websites:  # used as an integration without the prefilled template: take the triggering run's dataset
            res = (inp.get('payload') or {}).get('resource') or {}
            ds_id = dataset_id_from(str(res.get('defaultDatasetId') or '')) if isinstance(res, dict) else ''
        max_n = int(inp.get('maxBusinesses') or 100)
        opts = {
            'includePitch': inp.get('includePitch', True) is not False,
            'includeNoWebsite': inp.get('includeNoWebsite', True) is not False,
            'checkMx': inp.get('checkMx', True) is not False,
            'maxSubpages': max(0, min(5, int(inp.get('maxSubpages', 3) if inp.get('maxSubpages') is not None else 3))),
        }
        only_new = bool(inp.get('onlyNew'))
        conc_req = max(1, min(50, int(inp.get('maxConcurrency') or 20)))
        mem = Actor.configuration.memory_mbytes if Actor.is_at_home() else None
        # ~1 parallel site per 40 MB: parsing HTML is CPU bound and Apify gives 1 CPU core per 4096 MB
        conc = min(conc_req, max(4, mem // 40)) if mem else conc_req
        timeout_at = Actor.configuration.timeout_at  # ACTOR_TIMEOUT_AT; None for local runs without it
        if timeout_at is not None and timeout_at.tzinfo is None:
            timeout_at = timeout_at.replace(tzinfo=timezone.utc)

        def secs_left() -> float:
            return (timeout_at - datetime.now(timezone.utc)).total_seconds() if timeout_at else float('inf')

        stop_new_before = STOP_NEW_BEFORE_SECS
        hard_stop_before = HARD_STOP_BEFORE_SECS
        if timeout_at and secs_left() < 4 * STOP_NEW_BEFORE_SECS:  # very short runs: scale the margins down
            stop_new_before = max(25.0, secs_left() * 0.25)
            hard_stop_before = max(18.0, secs_left() * 0.15)

        leads: list[dict[str, Any]] = []
        for i, w in enumerate(websites):
            name = names[i] if i < len(names) else None
            if '|' in w:
                name, w = split_name_site(w, name)
            leads.append({'source': 'list', 'businessName': name, 'inputWebsite': w})
        if ds_id:
            Actor.log.info(f'Reading Google Maps dataset {ds_id} ...')
            try:
                ds = await Actor.open_dataset(id=ds_id, force_cloud=Actor.is_at_home() or bool(Actor.configuration.token))
                async for it in ds.iterate_items():
                    leads.append(lead_from_maps(it))
                    if len(leads) >= max_n * 3 + 200:
                        break
            except Exception as ex:
                err = str(ex).rstrip('.')
                hint = ('Use a Google Maps scraper dataset from YOUR account (Storage tab of that run), or paste websites instead. '
                        'A dataset ID from another account only works if that dataset is public.')
                if 'permission' in err.lower() or 'Insufficient' in err:
                    hint = ('This Actor can only read datasets you own or that are public. '
                            'Open your Maps scraper run → Storage → copy that dataset ID, or paste websites instead.')
                await _input_error(f'Could not read dataset "{ds_id}": {err}. {hint}')
                return
        if not leads:
            await _input_error('Nothing to audit: provide "websites" (URLs or domains) or a Google Maps "mapsDatasetId"'
                               + (f' (dataset {ds_id} is empty).' if ds_id else '.'))
            return

        # de-duplicate by domain (or place / name for no-website rows)
        uniq: list[dict[str, Any]] = []
        seen: set[str] = set()
        closed = 0
        for ld in leads:
            if ld.get('permanentlyClosed'):
                closed += 1
                continue
            u = A.normalize_url(ld.get('inputWebsite') or '') if ld.get('inputWebsite') else None
            key = A.domain_of(u) if u and not A.is_social_url(u) else f"place:{ld.get('placeId') or ld.get('businessName') or ld.get('inputWebsite')}"
            ld['_key'] = key
            if key in seen:
                continue
            seen.add(key)
            uniq.append(ld)

        state_store = None
        state: dict[str, Any] = {'audited': {}}
        skey = state_key(inp.get('monitorKey') or ds_id or 'default')
        skipped_old = 0
        if only_new:
            state_store = await Actor.open_key_value_store(name=STATE_STORE)
            state = await state_store.get_value(skey) or {'audited': {}}
            before = len(uniq)
            uniq = [ld for ld in uniq if ld['_key'] not in state['audited']]
            skipped_old = before - len(uniq)
            Actor.log.info(f'onlyNew: skipping {skipped_old} businesses audited in earlier runs (key "{skey}").')
        uniq = uniq[:max_n]
        Actor.log.info(f'Auditing {len(uniq)} businesses (concurrency {conc}'
                       + (f', memory {mem} MB' if mem else '') + (f', {int(secs_left())}s until run timeout' if timeout_at else '') + ').')
        await Actor.set_status_message(f'Auditing {len(uniq)} businesses...')

        f = Fetcher(inp.get('proxyConfiguration'), inp.get('proxyFallback', True) is not False, conc)
        await f.init()
        out = Output()
        sem = asyncio.Semaphore(conc)
        stats = Counter()
        grades = Counter()
        scores: list[int] = []
        done = 0
        started: set[str] = set()
        finished: set[str] = set()
        t_start = time.monotonic()

        async def work(ld: dict[str, Any]) -> None:
            nonlocal done
            async with sem:
                if out.limit_hit or secs_left() <= stop_new_before:
                    return
                started.add(ld['_key'])
                budget = min(SITE_TIMEOUT_SECS, max(5.0, secs_left() - hard_stop_before))
                try:
                    row, chargeable, contact = await asyncio.wait_for(audit_lead(f, ld, opts), timeout=budget)
                except Exception as ex:
                    row = {'businessName': ld.get('businessName'), 'inputWebsite': ld.get('inputWebsite'), 'source': ld.get('source'),
                           'status': 'error', 'statusDetail': f'{type(ex).__name__}: {str(ex)[:200]}', 'auditedAt': now_iso()}
                    chargeable, contact = False, False
                ok = await out.push(row, chargeable, contact)
                finished.add(ld['_key'])
                if not ok:
                    return
                stats[row['status']] += 1
                if chargeable:
                    grades[row['grade']] += 1
                    scores.append(row['problemScore'])
                    state['audited'][ld['_key']] = row['auditedAt'][:10]
                if contact:
                    stats['withSiteContact'] += 1
                done += 1
                if done % 10 == 0:
                    rate = done / max(1.0, time.monotonic() - t_start) * 60
                    await Actor.set_status_message(f'Audited {done}/{len(uniq)} businesses ({rate:.0f}/min)...')

        time_limited = False
        tasks = [asyncio.create_task(work(ld)) for ld in uniq]
        try:
            wait_s = max(1.0, secs_left() - hard_stop_before) if timeout_at else None
            _, pending = await asyncio.wait(tasks, timeout=wait_s)
            if pending:
                time_limited = True
                for t in pending:
                    t.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
        finally:
            await f.close()
        if not out.limit_hit:
            left = [ld for ld in uniq if ld['_key'] not in finished]
            if left:
                time_limited = True
                Actor.log.warning(f'Run time limit: {len(left)} businesses were not audited; saving them as {ST_TIME} rows (not charged).')
                await Actor.push_data([{
                    'businessName': ld.get('businessName'), 'inputWebsite': ld.get('inputWebsite'), 'source': ld.get('source'),
                    'domain': A.domain_of(A.normalize_url(ld.get('inputWebsite') or '') or '') if ld.get('inputWebsite') else None,
                    'status': ST_TIME, 'statusDetail': 'The run reached its time limit before this business was audited. Not charged; rerun to audit it.',
                    'auditedAt': now_iso()} for ld in left])
                stats[ST_TIME] += len(left)
                out.pushed += len(left)

        if state_store is not None:
            aud = state['audited']
            if len(aud) > 100000:
                state['audited'] = dict(sorted(aud.items(), key=lambda x: x[1])[-100000:])
            await state_store.set_value(skey, state)

        summary = {
            'finishedAt': now_iso(), 'inputRows': len(leads), 'uniqueBusinesses': len(seen), 'permanentlyClosedSkipped': closed,
            'skippedAlreadyAudited': skipped_old, 'rowsOutput': out.pushed, 'byStatus': dict(stats), 'byGrade': dict(grades),
            'avgProblemScore': round(sum(scores) / len(scores), 1) if scores else None,
            'chargedEvents': dict(out.charged), 'httpRequests': f.requests, 'proxyFallbackRequests': f.proxy_requests,
            'stoppedAtChargeLimit': out.limit_hit, 'stoppedAtTimeLimit': time_limited, 'concurrency': conc,
            'memoryMbytes': mem, 'elapsedSecs': round(time.monotonic() - t_start, 1),
        }
        await Actor.set_value('SUMMARY', summary)
        msg = (f"Audited {out.charged[EV_AUDIT]} businesses ({stats['withSiteContact']} with owner/email found); "
               f"{stats['blocked']} blocked, {stats['down']} down, {stats['noWebsite']} without a website.")
        if skipped_old:
            msg += f' {skipped_old} skipped (already audited in earlier runs).'
        if out.limit_hit:
            msg += ' Stopped early: maximum charge for this run reached.'
        if time_limited:
            msg += f' Stopped early: run time limit reached, {stats[ST_TIME]} not audited (not charged, rerun with a longer timeout or more memory).'
        await Actor.set_status_message(msg[:900], is_terminal=True)
