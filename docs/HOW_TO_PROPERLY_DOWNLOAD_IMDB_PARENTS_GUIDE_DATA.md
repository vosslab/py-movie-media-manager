# How to properly download IMDB parental guide data

Lessons learned from implementing parental guide scraping in this project.

## The problem

IMDB does not include parental guide (content advisory) data in their
[public data dumps](https://datasets.imdbws.com/). The TSV files cover
titles, ratings, people, and crew, but not advisory categories like
"Sex & Nudity" or "Violence & Gore." Parental guide data is only available
through the IMDB website or their GraphQL API.

## Why naive HTTP requests fail

IMDB protects their website with AWS WAF (Web Application Firewall). A
plain `requests.get()` or `urllib` call receives an HTTP 202 response with
a JavaScript challenge instead of the actual page content. The challenge
requires a browser-like environment to solve.

## What works

### IMDB GraphQL API via curl_cffi (recommended)

The IMDB GraphQL API at `https://api.graphql.imdb.com/` returns parental
guide severity data directly without HTML scraping. Use `curl_cffi` with
`impersonate='chrome'` for TLS fingerprinting.

```python
import curl_cffi.requests

query = (
    "query ParentsGuide($titleId: ID!) {"
    "  title(id: $titleId) {"
    "    parentsGuide {"
    "      categories {"
    "        category { id text }"
    "        severity { text }"
    "      }"
    "    }"
    "  }"
    "}"
)
payload = {"query": query, "variables": {"titleId": imdb_id}}
response = curl_cffi.requests.post(
    "https://api.graphql.imdb.com/",
    json=payload, impersonate="chrome", timeout=15,
)
data = response.json()
# data["data"]["title"]["parentsGuide"]["categories"] contains the results
# returns null for movies without parental guide data
```

Advantages:
- No browser engine or HTML parsing needed
- Works from any thread (no Qt main thread requirement)
- Fast (sub-second response times)
- Returns structured data directly
- Distinguishes "no data available" (`categories: null`) from fetch failures

### QWebEnginePage browser transport (fallback)

A full Chromium engine (`QWebEnginePage`) can load the page and solve the
WAF JavaScript challenge automatically. This works but has significant
drawbacks:
- Must run on the Qt main thread (requires thread bridging from workers)
- WAF challenge + redirect + page load can take 5-20 seconds
- Timeout failures are common (`loadFinished never fired`)
- Requires a running Qt application with an event loop

### Headless Chrome via Selenium

Lars Ingebrigtsen's [`imdb.el/get-html.py`](https://github.com/larsmagne/imdb.el)
uses headless Chrome through Selenium to bypass WAF. This works but carries
the overhead of spawning a full browser process per request.

## What does not work

| Approach | Why it fails |
| --- | --- |
| Plain `requests` / `urllib` | No TLS fingerprint, no JS execution; WAF returns HTTP 202 challenge |
| `curl_cffi` without `impersonate` | Same as plain requests; WAF detects non-browser TLS |
| Copying cookies from browser to `requests` | WAF token is bound to the TLS session that solved the challenge |
| Retry loops on HTTP 202 | Once blocked, retrying increases blocking likelihood |
| HTML scraping for `__NEXT_DATA__` | `contentData.categories` is now always `null`; severity data moved to GraphQL |

## Extracting the data

### GraphQL API (current, recommended)

```
POST https://api.graphql.imdb.com/
Response: data.title.parentsGuide.categories[]
  .category.text  -> "Sex & Nudity"
  .severity.text  -> "Moderate"
```

Returns `categories: null` for movies without parental guide data.

### HTML `__NEXT_DATA__` paths (deprecated)

These paths previously contained severity data but `contentData.categories`
now returns `null`. The data has moved to the GraphQL API.

```
# curl_cffi HTML response (no longer works)
props.pageProps.contentData.categories[]
  .title          -> "Sex & Nudity"
  .severitySummary.text -> "Moderate"

# Browser-rendered page (no longer works)
props.pageProps.contentData.section.items[]
  .id             -> "advisory-nudity"
  .severityVote.severity -> "Moderate"

# Older page versions
props.pageProps.aboveTheFoldData.parentsGuide.categories[]
  .category.text  -> "Sex & Nudity"
  .severity.text  -> "Moderate"
```

## Rate limiting

IMDB applies per-IP rate limits independent of WAF challenges. Add a
`time.sleep(random.random())` pause before each request to stay under
the limit. See [docs/WAF_CHALLENGES.md](docs/WAF_CHALLENGES.md) for
full WAF documentation.

## Implementation in this project

The parental guide fetch is implemented in
[moviemanager/scraper/imdb_scraper.py](moviemanager/scraper/imdb_scraper.py):

- `_fetch_parental_guide_graphql()` -- primary transport via IMDB GraphQL API
- `get_parental_guide()` -- tries GraphQL first, falls back to browser transport
- `_parse_parental_guide_html()` -- parser for browser-rendered JSON path (fallback)
- `_parse_parental_guide_from_above_fold()` -- parser for older JSON path (fallback)
