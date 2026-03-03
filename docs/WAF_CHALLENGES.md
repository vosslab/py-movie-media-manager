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

### Metadata and parental guide (QWebEnginePage transport)

IMDB title pages and parental guide pages are loaded via `QWebEnginePage`,
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

## Configuration

Cookies are stored in `~/.cache/movie_organizer/webengine/`. Clearing this
directory resets the WAF immunity tokens and forces re-challenge on the next
request.

The custom User-Agent string is defined in
[moviemanager/ui/imdb_browser_transport.py](moviemanager/ui/imdb_browser_transport.py).
