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
