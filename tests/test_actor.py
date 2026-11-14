from pathlib import Path

from bs4 import BeautifulSoup

from src import audit as A
from src.main import is_blocked, lead_from_maps, dataset_id_from

HTML = (Path(__file__).parent / 'fixtures' / 'plumber.html').read_text()
SOUP = BeautifulSoup(HTML, 'lxml')


def test_normalize():
    assert A.normalize_url('joespizza.com') == 'https://joespizza.com/'
    assert A.domain_of('https://www.Example.com/x') == 'example.com'
    assert A.normalize_url('not a url') is None
    assert A.is_social_url('https://www.facebook.com/page')


def test_checks():
    c = A.page_checks(HTML, SOUP)
    assert c['builder'] == 'WordPress' and c['generator'] == 'WordPress 5.2'
    assert c['analytics'] == ['Google Analytics 4'] and c['adPixels'] == []
    assert c['copyrightYear'] == 2019 and c['hasContactForm'] and not c['mobileViewport']
    assert c['hasLocalBusinessSchema'] and c['hasH1'] and c['metaDescription'] is None


def test_contacts_people():
    ct = A.extract_contacts(SOUP, HTML, 'https://smithplumbing.com/')
    assert 'bob@smithplumbing.com' in ct['emails'] and 'info@smithplumbing.com' in ct['emails']
    assert ct['socials'] == {'facebook': 'https://www.facebook.com/smithplumbingatx'}
    assert len(ct['phones']) == 1
    ppl = A.extract_people(SOUP, HTML, 'https://smithplumbing.com/')
    names = [p['name'] for p in ppl]
    assert names[0] == 'Robert Smith' and 'Maria Lopez' in names
    assert all('Book' not in n for n in names)
    assert A.email_kind('info@x.com') == 'generic' and A.email_kind('bob@x.com') == 'personal'


def test_subpages():
    subs = A.find_subpages(SOUP, 'https://smithplumbing.com/', 3)
    assert 'https://smithplumbing.com/about-us/' in subs and 'https://smithplumbing.com/our-team' in subs


def test_score_pitch():
    c = A.page_checks(HTML, SOUP)
    c.update({'https': True, 'responseTimeMs': 4000, 'hasEmail': True, 'hasSocialLinks': True})
    issues = A.collect_issues(c, 3.6, 12, 'ok')
    assert 'NOT_MOBILE_FRIENDLY' in issues and 'SLOW' in issues and 'OUTDATED_COPYRIGHT' in issues and 'LOW_RATING' in issues
    s, g = A.score(issues)
    assert 0 < s <= 100 and g in 'ABCDF'
    angle, opener, prim = A.pitch(issues, {'businessName': 'Smith Plumbing', 'domain': 'smithplumbing.com', 'ownerName': 'Robert Smith',
                                           'category': 'Plumber', 'city': 'Austin', 'responseTimeMs': 4000})
    assert prim == 'NOT_MOBILE_FRIENDLY' and opener.startswith('Hi Robert,') and 'Austin' in opener
    assert A.score(['NO_WEBSITE']) == (100, 'F')


def test_blocked_and_maps():
    assert is_blocked(403, '')
    assert is_blocked(405, '<title>Human Verification</title>')
    assert not is_blocked(200, '<html>' + 'x' * 30000)
    ld = lead_from_maps({'title': 'Joe', 'website': 'https://joe.com/?utm=gmb', 'totalScore': 4.2, 'reviewsCount': 8,
                         'categoryName': 'Pizza restaurant', 'city': 'Austin', 'url': 'https://www.google.com/maps/place/x'})
    assert ld['rating'] == 4.2 and ld['reviewCount'] == 8 and ld['mapsUrl']
    assert dataset_id_from('https://api.apify.com/v2/datasets/AbCdEf12345/items') == 'AbCdEf12345'


GOOD = {'https': True, 'sslInvalid': False, 'httpRedirectsToHttps': True, 'mobileViewport': True, 'responseTimeMs': 800,
        'pageSizeKb': 300, 'titleLength': 50, 'metaDescription': 'x' * 120, 'hasH1': True, 'copyrightYear': A.YEAR,
        'analytics': ['Google Tag Manager'], 'adPixels': ['Meta Pixel'], 'bookingTools': ['Housecall Pro'], 'hasContactForm': True,
        'chatWidgets': [], 'hasLocalBusinessSchema': True, 'hasSocialLinks': True, 'flashOrLegacy': False, 'hasEmail': True,
        'hasClickToCall': True, 'hasReviewsOnSite': True}


def test_scoring_v2_bands():
    # a site that passes every check is an A with score 0
    assert A.collect_issues(GOOD, 4.9, 300, 'ok') == [] and A.score([]) == (0, 'A')
    # one small gap stays A, two medium gaps fall to B or worse
    assert A.score(['NO_SOCIAL_LINKS']) == (4, 'A') and A.score(['NO_AD_PIXEL']) == (6, 'B')
    assert A.score(['NO_ANALYTICS'])[1] == 'B' and A.score(['NO_ANALYTICS', 'NO_LOCAL_SCHEMA'])[1] == 'C'
    # no way to convert a visitor is at least a C on its own
    assert A.score(['NO_LEAD_CAPTURE'])[1] == 'C'
    assert A.score(['NO_LEAD_CAPTURE', 'NO_ANALYTICS', 'NO_CLICK_TO_CALL'])[1] == 'F'
    assert A.score(['SITE_DOWN']) == (100, 'F') and A.score(['NO_HTTPS', 'NOT_MOBILE_FRIENDLY', 'NO_LEAD_CAPTURE'])[0] == 80
    for bound, g in A.GRADE_BANDS:
        assert A.score_to_grade(bound) == g and A.score_to_grade(bound + 1) != g


def test_scoring_v2_new_checks_and_old_rows():
    c = dict(GOOD, hasClickToCall=False, hasReviewsOnSite=False, responseTimeMs=3000)
    issues = A.collect_issues(c, None, None, 'ok')
    assert issues == ['SLOW', 'NO_CLICK_TO_CALL', 'NO_REVIEWS_ON_SITE']
    # saved rows from scoring v1 have no hasClickToCall / hasReviewsOnSite keys: not flagged
    old = {k: v for k, v in GOOD.items() if k not in ('hasClickToCall', 'hasReviewsOnSite')}
    assert A.collect_issues(old, None, None, 'ok') == []
    assert set(A.POINTS) == set(A.ISSUE_TEXT) and all(k in A.SEVERITY for k in A.POINTS)


def test_page_checks_tel_and_reviews():
    html = ('<html><head><title>Joe Plumbing Austin</title></head><body><h1>Joe</h1>'
            '<a href="tel:+15125550100">Call</a><section><h2>What our customers say</h2></section></body></html>')
    c = A.page_checks(html, BeautifulSoup(html, 'lxml'))
    assert c['hasClickToCall'] and c['hasReviewsOnSite']
    bare = '<html><head><title>Joe Plumbing Austin</title></head><body><h1>Joe</h1><p>Call 512-555-0100</p></body></html>'
    c2 = A.page_checks(bare, BeautifulSoup(bare, 'lxml'))
    assert not c2['hasClickToCall'] and not c2['hasReviewsOnSite']
    widget = '<html><body><div class="elfsight-app-123"></div><a href="/reviews/">x</a></body></html>'
    assert A.page_checks(widget, BeautifulSoup(widget, 'lxml'))['hasReviewsOnSite']


def test_split_name_site():
    from src.main import split_name_site
    assert split_name_site('Joe Pizza | joespizza.com') == ('Joe Pizza', 'joespizza.com')
    assert split_name_site('joespizza.com | Joe Pizza') == ('Joe Pizza', 'joespizza.com')
    assert split_name_site('Austin Roofing Company & Water Damage | WDR | https://austinroofingandwaterdamage.com/') == (
        'Austin Roofing Company & Water Damage | WDR', 'https://austinroofingandwaterdamage.com/')
    assert split_name_site('no site here | WDR', 'X') == ('X', 'no site here | WDR')
