# WAF challenges

How this application handles AWS WAF challenges on IMDB.

## What AWS WAF does

IMDB uses Amazon Web Services (AWS) Web Application Firewall (WAF) to
protect their endpoints. WAF applies two main controls:

- **JavaScript challenge**: HTTP 202 + `x-amzn-waf-action: challenge` header.
  The response body contains JavaScript the browser must execute. After solving,
  an `aws-waf-token` cookie grants an immunity window for subsequent requests.
- **Rate limiting**: Per-IP request limits over a time window. Independent of
  the JS challenge mechanism.

The JS challenge is transparent -- no user interaction is required. A real
browser engine solves it automatically by executing the JavaScript.

## Why curl_cffi and cookie transfer fail

| Approach | Problem |
| --- | --- |
| curl_cffi with browser TLS fingerprint | WAF checks more than TLS: JS execution context, timing, browser APIs |
| Copying cookies from browser to curl_cffi | Session binding ties cookies to TLS fingerprint and JS context |
| Retry on HTTP 202 | Once blocked, retrying increases blocking likelihood |

The WAF token is bound to the session context that solved the challenge.
Transplanting cookies between contexts (browser to curl_cffi, Firefox to
QWebEngine) does not preserve the binding, so the token is rejected.

## How this app handles WAF

### Search (no WAF)

The CDN suggestion endpoint `v2.sg.media-imdb.com/suggestion/titles/x/{query}.json`
has no WAF protection. The app uses plain HTTP (`requests`) for search.

### Parental guide (GraphQL API primary, QWebEnginePage fallback)

Parental guide data is fetched via the IMDB GraphQL API at
`https://api.graphql.imdb.com/` using `curl_cffi` with
`impersonate='chrome'` for TLS fingerprinting. This is faster and more
reliable than HTML scraping -- the `__NEXT_DATA__` JSON on the parental
guide page no longer contains severity data (IMDB moved it to lazy-loaded
GraphQL). The GraphQL response returns `categories[].category.text` and
`categories[].severity.text`, or `categories: null` for movies without
parental guide data.

If the GraphQL request itself fails (network error, non-200 status), the
scraper falls back to the QWebEnginePage browser transport described below.
Movies that simply have no parental guide data return an empty dict without
triggering the fallback.

### Metadata (QWebEnginePage transport)

IMDB title pages are loaded via `QWebEnginePage`,
which is a full Chromium browser engine. Key details:

- **Custom User-Agent**: The default `QtWebEngine` user agent is banned by IMDB.
  The transport sets a standard Chrome user agent string.
- **Persistent cookies**: `QWebEngineProfile` stores cookies on disk at
  `~/.cache/movie_organizer/webengine/`. The `aws-waf-token` cookie persists
  across requests and app restarts, so subsequent requests within the immunity
  window pass without re-challenge.
- **Automatic JS execution**: When a WAF JS challenge is returned, the Chromium
  engine executes it automatically. The page then redirects to the actual content.
- **Rate limiting**: The app waits `1 + random()` seconds between requests to
  stay under IMDB's per-IP rate limit.

### Thread bridging

`QWebEnginePage` must run on the Qt main thread. The scraper runs on worker
threads. The transport bridges them:

1. Worker thread calls `transport.fetch_html(url)`
2. Signal emitted to Qt main thread, `QWebEnginePage.load(url)` called
3. Chromium solves any WAF JS challenge during page load
4. `loadFinished` fires, `toHtml()` extracts HTML content
5. `threading.Event` set, worker thread unblocks with the HTML

### CAPTCHA fallback

If IMDB ever upgrades from JS challenge to CAPTCHA (requiring human
interaction), the `ImdbChallengeDialog` shows the page in a visible
`QWebEngineView`. The user solves the CAPTCHA manually. The dialog shares
the same `QWebEngineProfile` as the transport, so the solved CAPTCHA's
cookies immediately apply to subsequent transport requests.

## Immunity window

The WAF immunity window duration is controlled by AWS on the server side.
This app does not control or predict it. During the window, requests pass
without challenge. After expiry, the next request triggers a new JS challenge
which the Chromium engine solves automatically.

## Rate limiting

Separate from WAF challenges, IMDB has per-IP rate limits. The app applies:

- `time.sleep(random.random())` before CDN suggestion API calls
- `time.sleep(1 + random.random())` before QWebEnginePage loads (max ~1 req/sec)

This reduces the chance of triggering rate-limit blocks.

## Diagnostic logging

The transport logs each stage of the fetch pipeline so timeout failures
indicate exactly where the process stalled. Log messages use the
`moviemanager.ui.imdb_browser_transport` logger at INFO/WARNING level.

Stages tracked:

| Stage | Log message | Meaning |
| --- | --- | --- |
| fetch start | `[worker-thread] fetch_html starting` | Worker thread initiated the request |
| signal emitted | `[worker-thread] _load_requested emitted` | Signal sent to Qt main thread |
| load finished | `loadFinished fired: ok=True/False` | Chromium completed (or failed) the network load |
| HTML received | `toHtml callback received` | Page HTML extracted from Chromium |
| event wait done | `[worker-thread] event.wait returned` | Worker thread unblocked |

Timeout error messages include a stage label in parentheses:

- `(loadFinished never fired)` -- Chromium never completed the page load.
  Likely causes: WAF JS challenge taking longer than the timeout, network
  stall, or Qt event loop starvation preventing the main thread from
  processing the load.
- `(toHtml callback never returned)` -- Chromium loaded the page but the
  `toHtml()` callback never fired. Rare; may indicate a renderer crash.

## Timeout tuning

The parental guide fetch uses a 15-second timeout (`timeout_sec=15`).
The general metadata fetch uses the default 30-second timeout. WAF JS
challenges can take 5-20 seconds to solve depending on network and server
conditions, and include at least one redirect after solving. If the first
request in a session triggers a WAF challenge, 15 seconds may not be enough
for challenge + redirect + page load.

Symptoms of a too-short timeout:

- All parental guide fetches fail with `loadFinished never fired`
- Failures happen in bursts (all requests in a batch fail identically)
- Metadata fetches for the same movies succeed (they use 30s timeout)

Recovery options:

- Retry the batch -- the first failed request may have solved the WAF
  challenge, granting immunity for subsequent attempts
- Clear `~/.cache/movie_organizer/webengine/` to force a fresh WAF token
  if the cached token has become invalid

## IMDB data dumps (alternative data source)

IMDB publishes daily TSV data dumps at `https://datasets.imdbws.com/`
containing structured data (movies, ratings, people, crew, episodes).
These files have no WAF protection and require no browser engine.

However, the data dumps do **not** include parental guide / content
advisory data. That information is only available on the IMDB website,
which is why `curl_cffi` (or the browser transport fallback) is required
for parental guide fetches.

Other tools that scrape IMDB (such as Lars Ingebrigtsen's `imdb-mode`
for Emacs) use a similar two-layer approach: data dumps for structured
data, headless Chrome (via Selenium) for web-only content like images.

## Configuration

Cookies are stored in `~/.cache/movie_organizer/webengine/`. Clearing this
directory resets the WAF immunity tokens and forces re-challenge on the next
request.

The custom User-Agent string is defined in
[moviemanager/ui/imdb_browser_transport.py](moviemanager/ui/imdb_browser_transport.py).
