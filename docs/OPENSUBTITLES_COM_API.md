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

## System status

Check API status at the [OpenSubtitles status page](https://status.opensubtitles.com/).
