# OpenSubtitles.com REST API

Reference for the OpenSubtitles.com REST API used by this project for subtitle
search and download.

Source: [OpenSubtitles API docs](https://opensubtitles.stoplight.io/docs/opensubtitles-api/e3750fd63a100-getting-started)

## Authentication

The API uses two authentication mechanisms:

- **API key** (static, per-application): sent as HTTP header `Api-Key`. One key
  per application is mandatory. Users should not create their own API keys.
- **JWT token** (per-user): sent as HTTP header `Authorization: Bearer <token>`.
  Required for downloading subtitles and fetching user info.

Users must be authenticated for two endpoints:

- `/infos/user` (user info)
- `/download` (subtitle download)

JWT tokens are valid for 24 hours. If the API returns HTTP 500 with an "invalid"
message, re-authenticate the user.

## Download limits

- Without user auth: 5 downloads per IP per 24 hours.
- Signed-up user: 20 downloads per day.
- VIP user: up to 1000 downloads per day.
- Search (`/subtitles`) has no rate limit.
- Download counters reset at midnight UTC.
- During development, set the consumer to "Under Development" for up to 100
  downloads per day without user auth.
- When the quota is exhausted, the `/download` endpoint returns HTTP 406 with a
  JSON body:

```json
{
  "requests": 20,
  "remaining": 0,
  "message": "You have downloaded your allowed 20 subtitles for 24h. Your quota will be renewed in HH hours and MM minutes (YYYY-MM-DD HH:MM:SS UTC) ts=...",
  "reset_time": "..."
}
```

## API key

Obtain an API key from the
[API consumers section](https://www.opensubtitles.com/en/consumers) of your
OpenSubtitles profile. The key must be included in every request.

API keys are for developers only. Do not allow end users to insert their own API
key (exception: API wrappers).

## Required HTTP request headers

Every request should include these headers. `Authorization` is required after
user login.

```
Accept: */*
Api-Key: <<API_KEY>>
Authorization: Bearer <<ACCESS_TOKEN>>
User-Agent: <<APP_NAME vAPP_VERSION>>
```

If `User-Agent` cannot be set, use `X-User-Agent` instead.

## Example requests

### Unauthenticated request (formats info)

```bash
curl -vvv --location "https://api.opensubtitles.com/api/v1/infos/formats" \
    -H "Content-Type: application/json" \
    -H "Api-Key: <<API_KEY>>" \
    -A "User-Agent: MyApp v0.1"
```

### Authenticated request (user info)

```bash
curl -vvv --location "https://api.opensubtitles.com/api/v1/infos/user" \
    -H "Content-Type: application/json" \
    -H "Api-Key: <<API_KEY>>" \
    -H "Authorization: Bearer <<ACCESS_TOKEN>>" \
    -A "User-Agent: MyApp v0.1"
```

### Subtitle search

```bash
curl -vvv --location "https://api.opensubtitles.com/api/v1/subtitles?imdb_id=133093" \
    -H "Content-Type: application/json" \
    -H "Api-Key: <<API_KEY>>" \
    -A "User-Agent: MyApp v0.1"
```

## HTTP response headers

The API supports CORS. Rate-limit info is returned in response headers:

```
content-type: application/json; charset=utf-8
ratelimit-reset: 1
ratelimit-limit: 5
ratelimit-remaining: 4
x-ratelimit-limit-second: 5
x-ratelimit-remaining-second: 4
access-control-allow-origin: *
access-control-allow-methods: GET, HEAD, POST, OPTIONS
access-control-allow-headers: Origin, Authorization, Accept, Api-Key, Content-Type, X-User-Agent
```

## Error responses

All error responses follow the standard HTTP pattern with a JSON body containing
`message` and optionally `status` fields:

```json
{
  "message": "error message/description",
  "status": 401
}
```

### 4xx client errors

**401 Unauthorized** - invalid username or password. Check user credentials.

```json
{"message": "Error, invalid username/password", "status": 401}
```

**403 Forbidden** - API key is wrong or missing. Check `Api-Key` header.

```json
{"message": "You cannot consume this service"}
```

Also returned when `User-Agent` header is wrong or missing. Set it to your app name
with version (e.g., `MyApp v1.2.3`).

**406 Not Acceptable** - multiple causes:

- Invalid `file_id` in `/download`:

```json
{"message": "Invalid file_id", "status": 406}
```

- Download quota exhausted in `/download`:

```json
{
  "requests": 21,
  "remaining": -1,
  "message": "You have downloaded your allowed 20 subtitles for 24h...",
  "reset_time": "23 hours and 57 minutes",
  "reset_time_utc": "2022-01-30T06:00:53.000Z"
}
```

- Invalid or expired JWT token sent to `/download`:

```json
{"message": "invalid token"}
```

- If response is 406 without any body, ensure the `Accept: */*` header is present
  on every request.

**410 Gone** - download link from `/download` has expired. Regenerate the link.

**429 Too Many Requests** - rate limit reached. Check HTTP response headers for
rate limit info and retry after cooling down.

```json
{"message": "Throttle limit reached. Retry later.", "status": 429}
```

### 5xx server errors

Transient server errors. Client should retry the same request after 1 second.

## Rate limits

API requests are rate limited to 5 requests per second per IP address. The
`/login` endpoint has a stricter limit of 1 request per second to prevent
credential flooding. Stop sending requests with the same credentials if
authentication fails.

Rate limit info is returned in response headers:

```
ratelimit-remaining: 4
ratelimit-reset: 1
ratelimit-limit: 5
x-ratelimit-remaining-second: 4
x-ratelimit-limit-second: 5
```

After the app finishes work, call `/logout` to free server resources.

## Best practices

- Always follow HTTP redirects (`--location` in curl). Some clients have 50%+
  redirects, which degrades response time and increases server load.
- Always set `User-Agent` to the app name with version (e.g.,
  `MovieMediaManager v1.0`). Missing or wrong values return 403.
- Always include the `Accept: */*` header on every request. Missing it can cause
  bare 406 responses with no body.

## Performance tips

For faster responses and fewer redirects on the `/subtitles` endpoint:

- Send GET parameters alphabetically sorted (including `page`).
- Send GET parameter names and values in lowercase.
- Remove `tt` prefix and leading zeros from IMDB IDs in GET values.
- Do not send default values (e.g., `ai_translated=include`,
  `machine_translated=exclude`).
- Use `+` instead of `%20` for spaces in URL encoding.

## Subtitle file encoding

All subtitles downloaded from the platform are UTF-8 encoded. Some subtitles
from opensubtitles.org are missing on opensubtitles.com because they could not
be converted from their original encoding or format.

## Subtitle formats

Default download format is SRT (UTF-8). To request another format, specify the
`sub_format` parameter in the `/download` endpoint.

## Movie hash

OpenSubtitles uses a simple hash to identify video files. See the
[OSDB movie hash source codes](https://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes)
for implementation details.

## Releasing your application

- Set the `User-Agent` header to your app name and version during development
  (e.g., `MyApp v0.1`). This helps OpenSubtitles debug requests.
- Contact OpenSubtitles before public release so they can add your app to their
  database.
- Never hardcode your own username and password in a public application. Users
  should authenticate with their own OpenSubtitles accounts.

## Debugging

Use [Insomnia](https://insomnia.rest/) or [Postman](https://www.postman.com/)
for debugging. Download the OpenAPI file from the docs site and import it.

Always include `--location` in curl commands to follow redirects.

## Implementation notes

This project's OpenSubtitles integration lives in two files:

- [moviemanager/scraper/subtitle_scraper.py](moviemanager/scraper/subtitle_scraper.py):
  low-level API client handling login, search, and download requests.
- [moviemanager/api/subtitle_service.py](moviemanager/api/subtitle_service.py):
  service layer managing JWT lifecycle, token freshness (23h max age), and quota
  tracking.

Key behaviors:

- The subtitle scraper is created by the registry pipeline with only an API key.
  The service layer authenticates it (calls `login()`) before the first download.
- JWT tokens are cached and reused across threads. Tokens older than 23 hours are
  automatically invalidated and re-authenticated (1h safety margin on 24h lifetime).
- On HTTP 401 during download, the service invalidates the token and retries once.
- On HTTP 406 with quota message, the service sets a session-level flag and
  immediately rejects all further download attempts without contacting the API.
- On HTTP 406 with "invalid token", the service invalidates the token for
  re-authentication on the next attempt.
- On HTTP 429 (rate limit), the service sets the quota flag to stop the batch.
- The scraper provides a `logout()` method that sends DELETE to `/logout` and
  clears the cached JWT token.

## System status

Check API status at the [OpenSubtitles status page](https://status.opensubtitles.com/).
