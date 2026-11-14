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
  "problemScore": 26,
  "grade": "B",
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
- **Automatic chain:** in the Maps scraper's **Integrations** tab, add this Actor with `{"mapsDatasetId": "{{resource.defaultDatasetId}}"}` so every Maps run is audited automatically.
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
  "problemScore": 26,
  "grade": "B",
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

### problemScore

Points per issue, capped at 100: no website / site down 100, broken site 85, no HTTPS or invalid SSL 20, not mobile-friendly 18, very slow (>6 s) 14, no booking/form/chat 10, low Google rating (<4.0) 9, no analytics 8, slow (>3 s) 8, outdated © year 7, missing title 7, few reviews 6, no http→https redirect 6, no ad pixel 5, missing meta description 5, heavy page 4, and smaller items (no H1, no LocalBusiness schema, no social links, no online booking) 2–3. Grades: A ≤20, B ≤40, C ≤60, D ≤80, F >80.

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

## More from LatentLark
- [Creator Commerce Competitor Finder (LTK & ShopMy)](https://apify.com/latentlark/creator-commerce-competitor-finder): find which creators promote any brand on LTK and ShopMy, with clicks, product counts and social links, plus new-affiliate alerts. No login.
- [Google Maps Rank Tracker (Geo-Grid Heatmap)](https://apify.com/latentlark/google-maps-rank-tracker): see where a business ranks on Google Maps across a city grid, a strong visual for the local-SEO pitch.
- [Google Sheets Export & Import (No OAuth)](https://apify.com/latentlark/sheets-export): send these leads to a Google Sheet on a schedule without Google login or expiring tokens.
- [Google Ads Transparency & LinkedIn Ad Library Scraper](https://apify.com/latentlark/competitor-ads-monitor): see which local competitors run Google or LinkedIn ads, a great add-on for the "no ad pixel" pitch.
- [Career Page Jobs API](https://apify.com/latentlark/ats-career-jobs): every open job from Workday, Personio, Greenhouse, Lever, Ashby and 3 more ATS as clean JSON, with only-new-jobs monitoring.
- [Telegram Channel Monitor](https://apify.com/latentlark/telegram-channel-monitor): public Telegram channel posts as JSON, with only-new-post monitoring.
