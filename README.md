# Google Maps No-Website Leads (Audit & Pitch)

**Find local businesses on Google Maps with no website or a weak one, and pitch them.** Built for web designers, SEO/marketing agencies and freelancers who sell to local businesses. Feed it a Google Maps lead list (or a list of websites) and get back the businesses that need you most: **businesses with no website at all**, plus sites that are broken, slow, insecure or not mobile-friendly. Each row has a 0–100 problemScore, the owner's name and email when published, and a ready **pitch angle + cold-email opener** built from the site's real gaps.

**Outcome:** a Maps export that was sitting unused becomes a call/email list you can work today, sorted by need (no website or worst website first), every pitch backed by a specific, verifiable reason.

- 🚫🌐 **No-website leads:** Maps listings without a website (or with only a Facebook page) come out as top-priority leads with problemScore 100.
- 🎯 **Who needs you most comes first:** sort by `problemScore` / `grade` (A–F). No website or a broken site scores 100.
- ✉️ **Pitches, not just data:** template-based opener from the biggest real issue (no AI cost, nothing invented).
- 👤 **Who to contact:** owner/founder name, emails (generic vs personal, MX check), phones, social profiles.
- 💸 **Pay only for results:** from $0.004 per business audited; blocked sites, errors and duplicates are free.

![Results: one row per business with problemScore, grade, top issue, owner name, email and a personalised cold email opener](https://api.apify.com/v2/key-value-stores/Tv899H9p8Kim9T8M2/records/local-lead-audit-results-table.png?signature=1uqtyt8a6vEdNoheocJts)

### Sample output (truncated)

```json
{
  "businessName": "Example Family Dentistry",
  "problemScore": 51,
  "grade": "F",
  "topIssues": ["No analytics installed", "No retargeting/ad pixel", "No booking, contact form or chat"],
  "ownerName": "Dr. Jane Smith",
  "emailOpener": "Hi Dr. Smith, I couldn't find a way to book or send a request on examplefamilydentistry.com. …"
}
```

### Pricing (pay per event, no subscription)

| Event | Price (free tier) |
|---|---|
| Actor start | $0.005 per run |
| Business audited | $0.004 |
| Contact found (owner name or website email) | $0.002 extra |

Example: 100 businesses, contacts found for 60 = $0.005 + 100 × $0.004 + 60 × $0.002 = **$0.525**. Bronze/Silver/Gold plans pay 10/20/30% less on audits and contacts.

**Need done-for-you setup (custom scrape or n8n wiring)?** → [Fiverr Apify scrape gig](https://www.fiverr.com/latent_lark/scrape-website-data-with-apify-into-clean-csv-excel-or-google-sheets) + [Fiverr n8n automation gig](https://www.fiverr.com/latent_lark/build-n8n-ai-automation-workflows-for-your-business)

## Quick start (first run in about 1 minute)

**Try it now:** the form is prefilled with 2 websites. Click **Start** and you get 2 audited leads in under a minute for about $0.02.

**With your own leads:**

1. Run any Google Maps scraper (for example `compass/crawler-google-places`) for e.g. *"plumber in Austin, TX"*.
2. In **Google Maps dataset** here, pick that run's dataset (or paste its dataset ID) and click **Start**.
3. Open the **Overview** tab: leads with the highest problemScore first, with owner name, email and a ready-made opener.

No Maps data? Paste website URLs into **Websites** instead (`Joe's Plumbing | joesplumbing.com` lets you add the business name too).

![Walkthrough: the prefilled form, click Start, then the audited leads in the Overview tab](https://api.apify.com/v2/key-value-stores/Tv899H9p8Kim9T8M2/records/local-lead-audit-walkthrough.gif?signature=TcPnXv4nPkWKRcDCx3hA)

## Google Maps chain / integrations

This Actor doesn't scrape Google Maps itself; it audits the output of a Maps scraper.

- **One-off:** run a Google Maps scraper (e.g. `compass/crawler-google-places`), then pick its dataset in **Google Maps dataset** here.
- **From Google Local Services Ads:** run [Google Local Services Ads Scraper](https://apify.com/latentlark/google-local-services-ads) for your trades and ZIPs, then set **Google Maps dataset** to that run's dataset. LSA rows already use `title`, `website`, `phone`, `categoryName`, `city`, `rating` and `reviewCount`. Turn off **Include Maps businesses without a website** if you only want sites that can be audited.
- **Automatic chain:** in the Maps scraper's or the LSA Actor's **Integrations** tab, add this Actor with `{"mapsDatasetId": "{{resource.defaultDatasetId}}"}` so every run is audited automatically.
- **To Google Sheets:** chain [Google Sheets Export](https://apify.com/latentlark/sheets-export) after it.
- **Any tool via API:** results are a normal Apify dataset, so n8n, Make, Zapier or your own code can read them through the Apify API or integrations.

## Run it on a schedule
Audit only the **new** businesses that show up in your Google Maps searches:

1. Schedule your Google Maps scraper (e.g. weekly *"dentist in Austin, TX"*).
2. In its **Integrations**, add this Actor with `{"mapsDatasetId": "{{resource.defaultDatasetId}}", "onlyNew": true, "monitorKey": "austin-dentists"}`.
3. Each week you get only the new, not-yet-audited leads. Optionally chain [Google Sheets Export](https://apify.com/latentlark/sheets-export) after it.

| Example | Cadence | Rough cost per month (this Actor) |
|---|---|---|
| About 50 new businesses a week, half with a contact found | weekly | **≈ $1.02** (4 starts × $0.005 + 200 audits × $0.004 + 100 contacts × $0.002) |
| About 20 new businesses a day | daily | ≈ $3.15 |

Your Google Maps scraper is billed separately. Free-tier prices; Bronze/Silver/Gold plans pay 10/20/30% less.

## What you can do with it

- **Web design / SEO agencies:** find local businesses with outdated, slow, insecure or non-mobile sites, or with no website at all, and pitch each one with a specific, verifiable reason.
- **Marketing / ads freelancers:** find businesses without analytics or ad pixels ("you can't retarget your visitors").
- **Booking / chat / review software sellers:** filter on `checks.bookingTools`, `checks.chatWidgets` and Maps rating.
- **Lead-gen sellers:** enrich a Maps export with owner names, emails and a qualification score before you sell or import it.
- **Monitoring:** schedule it with `onlyNew` to audit only businesses you haven't seen before.

### Everything it checks

- 🔎 **Website audit**: HTTPS/SSL, title & meta description, mobile viewport, H1, outdated © year, load time & page size, Google Analytics/GTM, Meta/TikTok/Google Ads pixels, online booking, live chat, contact forms, LocalBusiness schema, site builder (WordPress, Wix, Squarespace, GoDaddy, Shopify, Duda, Webflow…).
- ⭐ Keeps **Google Maps rating and review count** and flags low ratings or few reviews.
- 🔐 **Limited permissions:** it can read only the one dataset you pick, nothing else in your account.

## Input

| Field | Type | Description |
|---|---|---|
| `mapsDatasetId` | dataset | Dataset (ID or name) from a Google Maps scraper run (compass/crawler-google-places format and similar). Uses title, website, phone, rating, review count, category, city, emails. |
| `websites` | array | Website URLs or domains. Optional `Business Name \| domain.com` format. Can be combined with the dataset. |
| `businessNames` | array | Optional names matching `websites` by position. |
| `maxBusinesses` | integer | Maximum businesses to audit (default 100). |
| `includePitch` | boolean | Generate `pitchAngle` and `emailOpener` (default true). |
| `includeNoWebsite` | boolean | Also output Maps businesses with no website (no-website leads are great web-design leads). Default true. |
| `onlyNew` | boolean | Skip businesses audited in earlier runs (stored per `monitorKey`). |
| `monitorKey` | string | Name of the onlyNew memory, e.g. `austin-plumbers`. |
| `maxSubpages` | integer | About/team/contact pages to crawl per site to find owner and email (0–5, default 3). |
| `checkMx` | boolean | Check that the email domain accepts mail (default true). |
| `maxConcurrency` | integer | Upper bound for sites audited in parallel (default 20, max 50). The Actor lowers it to about 1 site per 40 MB of run memory, because page parsing is CPU bound. |
| `proxyFallback` | boolean | Retry blocked sites once through Apify **datacenter** proxy (default true). Residential is never used unless you set it. |

### Example inputs

From a Google Maps scraper dataset:
```json
{
  "mapsDatasetId": "YOUR_MAPS_DATASET_ID",
  "maxBusinesses": 200,
  "onlyNew": true,
  "monitorKey": "austin-plumbers"
}
```

From a list of websites:
```json
{
  "websites": ["Joe's Pizza | joespizzanyc.com", "https://www.example-dental.com"],
  "includePitch": true
}
```

## Output

One row per business. Example (shortened):

```json
{
  "businessName": "Example Family Dentistry",
  "website": "https://www.examplefamilydentistry.com/",
  "domain": "examplefamilydentistry.com",
  "category": "Dentist",
  "city": "Austin",
  "rating": 4.9,
  "reviewCount": 120,
  "status": "ok",
  "problemScore": 51,
  "grade": "F",
  "topIssues": ["No analytics installed", "No retargeting/ad pixel", "No booking, contact form or chat"],
  "issueCodes": ["NO_ANALYTICS", "NO_AD_PIXEL", "NO_LEAD_CAPTURE", "NO_LOCAL_SCHEMA"],
  "ownerName": "Dr. Jane Smith",
  "ownerTitle": "Owner and Lead Dentist",
  "primaryEmail": "info@…",
  "emailType": "generic",
  "emailMxValid": true,
  "phones": ["(512) …"],
  "socials": {"facebook": "https://facebook.com/…", "instagram": "https://instagram.com/…"},
  "checks": {"https": true, "sslValid": true, "builder": null, "analytics": [], "adPixels": [], "bookingTools": [], "chatWidgets": [], "hasContactForm": false, "copyrightYear": 2026, "responseTimeMs": 467, "pageSizeKb": 95},
  "pitchAngle": "Add online booking / a lead form",
  "emailOpener": "Hi Dr. Smith, I couldn't find a way to book or send a request on examplefamilydentistry.com. Visitors who don't want to phone have no way to reach you."
}
```

`status` is one of `ok`, `noWebsite`, `down`, `httpError`, `blocked` (bot protection, not charged), `error` (not charged), `invalidInput` (a Websites line that is not a URL or domain, not charged), `skippedTimeLimit` (the run reached its time limit before this business, not charged; rerun to audit it).

The run also saves a **SUMMARY** record in the key-value store: counts by status and grade, average problemScore, charged events, concurrency, memory and elapsed time.

### Speed, memory and time limits

- Default memory is **1024 MB** (a quarter of a CPU core on Apify). In our tests about 150 websites took about 3 minutes at 1024 MB, about 4 minutes at 512 MB and about 9 to 10 minutes at 256 MB. The Actor start fee is the same for any memory up to 1 GB.
- The Actor watches the run timeout. About 60 seconds before it, it stops starting new sites; unfinished ones are saved as `skippedTimeLimit` rows (free), and the run still ends **SUCCEEDED** with everything audited so far.
- Each site has a 60 second cap (homepage, up to 3 subpages and the MX check), so one slow site cannot hold up the run.

### problemScore and grade (scoring v2, November 2026)

Every issue code is worth a fixed number of points. problemScore is the sum, capped at 100, so the score and the grade always trace back to the issue codes in the row.

| Points | Issue codes |
|---|---|
| 100 | NO_WEBSITE, SITE_DOWN |
| 85 | SITE_ERROR |
| 30 | NO_HTTPS, INVALID_SSL |
| 25 | NOT_MOBILE_FRIENDLY, NO_LEAD_CAPTURE (no booking, contact form or chat) |
| 20 | VERY_SLOW (homepage over 5 s) |
| 12 | NO_ANALYTICS, LEGACY_TECH, LOW_RATING (Google rating under 4.0) |
| 10 | SLOW (over 2.5 s), MISSING_TITLE, OUTDATED_COPYRIGHT (2+ years old), NO_CLICK_TO_CALL (no tel: link) |
| 8 | NO_HTTPS_REDIRECT, MISSING_META_DESCRIPTION, NO_LOCAL_SCHEMA, FEW_REVIEWS (under 20) |
| 6 | NO_BOOKING (has a form but no online booking), NO_AD_PIXEL, NO_H1, NO_REVIEWS_ON_SITE (no reviews or testimonials shown) |
| 5 | HEAVY_PAGE (over 1.5 MB of HTML) |
| 4 | NO_EMAIL_ON_SITE, NO_SOCIAL_LINKS |

Grades: **A** 0 to 4 (at most one 4-point gap), **B** 5 to 14, **C** 15 to 26, **D** 27 to 38, **F** over 38. A site with no way to send a request (25 points) is a C on its own; add no analytics and no click-to-call and it is an F.

The weights were calibrated on 165 real websites of Google Local Services advertisers (Austin, November 2026). On that set the grades came out A 14%, B 37%, C 30%, D 7%, F 13%. The previous weights gave 87% A, because modern sites all pass HTTPS and mobile checks and the remaining gaps were only worth 2 to 5 points each.

Speed is only flagged when it is confirmed: a homepage that looks slow on the first fetch is timed again in a quiet worker thread and the faster time is used, so a busy run never makes a website look slow. `checks.responseTimeFirstMs` keeps the first timing when a re-check happened.

## Pricing

See the pricing table at the top. Larger example: 500 businesses with contacts found for 300 = $0.005 + 500 × $0.004 + 300 × $0.002 = **$2.61**.
Blocked sites, errors, duplicates, permanently closed listings and already-audited businesses (onlyNew) are **free**. Set a max charge per run in Apify and the Actor stops cleanly at the limit.

## Limitations

- Checks the homepage plus up to 5 about, team or contact pages. It isn't a full SEO crawl or Lighthouse test. Load time is measured server-side.
- Sites behind strong bot protection (Cloudflare challenges, AWS WAF) are marked `blocked` and not charged.
- Owner names are found from page text and structured data. Small sites often don't name the owner, so `ownerName` may be empty. `contactName` then holds the best other named person when there is one.
- The Actor finds only emails that are published on the website. It doesn't guess or verify mailboxes; the MX check only confirms the domain accepts mail.
- Pitch texts are templates. Review them before sending, and follow anti-spam and privacy rules (CAN-SPAM, GDPR) in your country.
- This Actor doesn't scrape Google Maps itself. Chain it after a Maps scraper dataset.

## FAQ

**Which Google Maps scraper works?** Any dataset with `title`, `website`, `phone` and optional `totalScore`/`reviewsCount`/`categoryName`/`city`, the format of compass/crawler-google-places. Common alternative field names (`name`, `rating`, `reviews`, `site`) are also recognised.

**Does it use AI?** No. Openers are deterministic templates filled with real findings, so there's no AI cost and nothing is invented.

**Can I run it on a schedule?** Yes. Use `onlyNew` with a `monitorKey` to pay only for new businesses.

**Can I send results to Google Sheets?** Yes, with our Google Sheets Export Actor below.

**Run says "Nothing audited" / dataset empty?** Paste a Maps scraper dataset that actually has rows, or use `websites` with a few domains. Empty or unreadable input ends SUCCEEDED with one explanatory row (not charged) so schedules stay green.

**"Insufficient permissions" on mapsDatasetId?** The dataset must be yours or public. Copy the ID from your own Maps scraper run's Storage tab (not someone else's private dataset). Or skip Maps and paste websites.

**Did this save you time?** A rating on the Store page helps other people find it. Missing a field or found a bug? Open an issue on the **Issues** tab, we usually reply within a day.

**Can you set this up for me?** Yes, see the done-for-you line at the top of this page.

**Can I audit Google Local Services Ads leads, not just Maps?** Yes. Run [Google Local Services Ads Scraper](https://apify.com/latentlark/google-local-services-ads) first, then set `mapsDatasetId` to that run's dataset. Providers with no website can be skipped with `includeNoWebsite: false`.

**Why did almost every site used to get an A?** Scoring v2 (November 2026) gives each issue a fixed number of points so the grade matches the real gaps. On 165 websites of Google Local Services advertisers in Austin, the grades came out A 14%, B 37%, C 30%, D 7%, F 13%. The previous weights gave 87% A, because modern sites already pass HTTPS and mobile checks and the leftover gaps were only worth 2 to 5 points each.

**Are blocked or failed sites charged?** No. `blocked`, `error`, `invalidInput`, `skippedTimeLimit`, duplicates, permanently closed listings and already-audited businesses (`onlyNew`) are free. You pay the $0.005 start plus $0.004 per business actually audited, and $0.002 extra when an owner name or website email is found (free-tier prices; Bronze / Silver / Gold pay 10 / 20 / 30% less).

**How long does 100 sites take?** In our tests about 150 websites took about 3 minutes at the default 1024 MB, about 4 minutes at 512 MB, and about 9 to 10 minutes at 256 MB. The start fee is the same for any memory up to 1 GB.

**What does problemScore 100 mean?** The business has no website (or only a Facebook page) or the site was down. Those are the highest-priority leads. A site with no way to send a request is 25 points (a C on its own); add no analytics and no click-to-call and it becomes an F (over 38).

**How should I sort a pitch list?** Sort by `problemScore` descending, or by `grade` with F first. Grades: A 0 to 4, B 5 to 14, C 15 to 26, D 27 to 38, F over 38. Agencies usually call D and F first, then C.

**Why is ownerName often empty?** Owner names are taken from page text and structured data only. Small sites often don't name the owner. `contactName` then holds the best other named person when there is one. Emails are only those published on the site; the MX check only confirms the domain accepts mail.

**Do I need a Google API key?** No. This Actor does not scrape Google Maps itself and does not use the Google Places API. You point it at a Maps or LSA dataset you already have, or paste websites.

## More from LatentLark
- [Google Local Services Ads Scraper (LSA Leads + Website)](https://apify.com/latentlark/google-local-services-ads): which plumbers, roofers, lawyers and other pros already pay for Google Local Services Ads in a city or ZIP. Feed that dataset into this Actor to audit the advertisers' websites.
- [Creator Commerce Competitor Finder (LTK & ShopMy)](https://apify.com/latentlark/creator-commerce-competitor-finder): find which creators promote any brand on LTK and ShopMy, with clicks, product counts and social links, plus new-affiliate alerts. No login.
- [Google Maps Rank Tracker (Geo-Grid Heatmap)](https://apify.com/latentlark/google-maps-rank-tracker): see where a business ranks on Google Maps across a city grid, a strong visual for the local-SEO pitch.
- [Google Sheets Export & Import (No OAuth)](https://apify.com/latentlark/sheets-export): send these leads to a Google Sheet on a schedule without Google login or expiring tokens.
- [Google Ads Transparency & LinkedIn Ad Library Scraper](https://apify.com/latentlark/competitor-ads-monitor): see which local competitors run Google or LinkedIn ads, a great add-on for the "no ad pixel" pitch.
- [Career Page Jobs API](https://apify.com/latentlark/ats-career-jobs): every open job from Workday, Personio, Greenhouse, Lever, Ashby and 3 more ATS as clean JSON, with only-new-jobs monitoring.
- [Telegram Channel Monitor](https://apify.com/latentlark/telegram-channel-monitor): public Telegram channel posts as JSON, with only-new-post monitoring.
