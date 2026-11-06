# Related projects

This guide points people managing large local movie libraries to the project's
documented inspiration, the NFO format it writes, and one adjacent media manager.

## Confirmed related projects

### tinyMediaManager

- Relationship: prior art
- Link: https://www.tinymediamanager.org/
- Why visitors may care: Both applications help people scan movie folders, collect metadata,
  write NFO files, and rename the files that make up a local library.
- Evidence: This project's package description says it is inspired by tinyMediaManager; the
  tinyMediaManager site describes movie metadata, NFO creation, and file and folder renaming.

### Kodi NFO files

- Relationship: domain standard/resource
- Link: https://kodi.wiki/view/NFO_files/Movies
- Why visitors may care: The application writes Kodi-compatible movie NFO XML beside video files,
  so this reference helps users understand file names, tags, and how Kodi imports local metadata.
- Evidence: [NFO file format](NFO_FILE_FORMAT.md) documents this project's Kodi NFO target, and
  the official Kodi Wiki documents movie NFO naming, location, and XML tags.

## Possible related projects

### MediaElch

- Relationship: same-workflow implementation
- Link: https://mediaelch.github.io/mediaelch-doc/
- Why visitors may care: It is another desktop workflow for browsing a local movie library,
  scraping and editing movie metadata, and storing it in NFO files.
- Evidence: MediaElch's official documentation describes it as a Kodi media manager whose movie
  section can browse, scrape, and edit movies stored as NFO files.
- Confidence: medium; the shared workflow is documented, but this repository does not identify
  a direct lineage or interoperability commitment with MediaElch.

## Evidence notes

The confirmed entries combine this repository's explicit tinyMediaManager inspiration and
Kodi-compatible NFO documentation with the official project and Kodi documentation. MediaElch is
included only as a documented adjacent workflow, not as a claim of feature parity or direct
integration.
