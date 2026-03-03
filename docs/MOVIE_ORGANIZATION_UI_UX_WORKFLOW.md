# Movie organization UI/UX workflow

## Two selection mechanisms

The movie table supports two independent selection mechanisms:

### Checkboxes (persistent batch selection)

- Toggled by clicking the checkbox column or using "Check X" buttons.
- Survives sorting, filtering, and scrolling.
- Intended for batch operations across many movies.
- "Check All", "Check None", "Check Unmatched", etc. set checkboxes by criteria.

### Row selection (transient highlight)

- Standard table highlight via click, Shift-click, or Cmd-click.
- Drives the detail panel on the right side.
- Lost when sorting or filtering changes.
- Useful for quick multi-select of a visible group.

## Bridging the two: "Check Selected"

The "Check Selected" button converts highlighted rows into checkboxes:

- Additive: does not uncheck anything first.
- Workflow: highlight rows with Shift/Cmd-click, then click "Check Selected" to persist the selection.

## Batch operation resolution order

All batch operations use `get_chosen_movies()` with this priority:

1. **Checked (2+)** -- if two or more checkboxes are active, use those.
2. **Selected (2+)** -- if two or more rows are highlighted, use those.
3. **Single checked** -- one checkbox active.
4. **Single selected** -- one row highlighted.
5. **Empty** -- nothing chosen.

For `_fetch_parental_guides()` and `_refresh_metadata()`, an empty result triggers
a fallback to all movies. Other operations show an error message instead.

## Context menu

Right-clicking a row opens a context menu for that single movie. The context menu is
independent of both checkboxes and row selection. It always acts on the right-clicked row.

## Button bar summary

| Button | Action |
| --- | --- |
| Check All | Check all visible movies |
| Check None | Uncheck all movies |
| Check Selected | Add highlighted rows to checked set |
| Check Unmatched | Check movies not yet matched to IMDB |
| Check Unorganized | Check movies not in proper folder structure |
| Check No PG | Check movies missing parental guide data |
| Check No Artwork | Check movies without poster artwork |
| Check No Subs | Check movies without subtitles |
