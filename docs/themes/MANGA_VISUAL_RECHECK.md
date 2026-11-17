# Manga Light visual recheck — 15 November 2026

Rechecked the 17 supplied reference folders against the isolated Qt renders.
The original screenshots and HTML were retained. The blank importer screenshot
was checked against its HTML instead. Standalone workflow renders omit the
shared application shell; that shell is checked in the complete Library render.

## Corrections in this pass

- **Add/Edit Entry:** one shared Manga rating/value control and the same form
  options. Selecting 7 fills 1–7; lowering or clearing removes the excess fill.
  Existing Sakura add controls remain synchronized. Creation and editing still
  use their respective save paths. The add-only custom-metadata notice remains.
- **Weekly schedule:** remove the accidental inner button face/border; keep a
  single outer card, reserve room for its shadow, split weekday/date and float
  TODAY over the outer edge. Existing preview/selection remains. A transfer bar
  appears only with actual progress, rather than an empty decorative track.
- **Details:** restore one inset personal band around watch status, rating and
  notes. Inactive statuses are transparent; the selected status stays pink.
  Ratings are compact and flat, with cumulative yellow fill. Notes have an
  inset surface and can still scroll/edit longer text.
- **Shared rules:** wrap existing inline declarations before appending selector
  rules. Mixing the two produced invalid QSS and could suppress state colours.
  Preserve native caption buttons outside the shared app-button policy.

## Reference review coverage

| Reference | Check and practical limit |
| --- | --- |
| Main Library | Hero, card border, controls, schedule, 6/7-card pagination and narrow/wide layouts checked |
| Anime Details | Personal band corrected; actions, episode/release rows retained |
| Edit Anime Entry | Shared form and cumulative rating checked with Add |
| Rematch Metadata | Light search/result/footer controls checked; retain existing multi-release confirmation |
| Updates | Light filters/actions and sorting checked; retain all existing disposition actions |
| Broadcast Updates | Light hero/table/actions checked; actual provider dates/data only |
| Review Downloads | Light summary/review controls checked; existing compact summary is simpler than the mockup's illustrated multi-panel layout |
| Downloads/Transfers | Queue/guide materials checked; queue render uses fixtures, not live downloads |
| Find Download Files | Search/context/results/actions checked; retain extra existing matching controls |
| Import Watched List | HTML used; existing matching/presence controls retained |
| Merge Libraries | Source/destination/preview/review materials checked; no sample moves executed |
| New Anime Releases | Uniform cards, filters and paging checked with temporary titles/artwork |
| Tags & Themes | Staged tag panel checked; no invented sample per-tag result counts |
| Organizer | Rules/roots/preview controls checked; no scan triggered for the visual check |
| View Changes | Light release rows/actions checked; actual saved events replace sample timeline text |
| Five-step Setup | Five existing steps on one scrolling page checked; no fake connection/integrity claims |
| Storage | Statistics/table/control materials checked with temporary records; no fake drive values |

## Fidelity limits

This confirms the reported material/control corrections, not pixel-identical
copies of every image. Font metrics, text wrapping and native window chrome can
differ. Existing extra controls remain where needed to preserve functionality.
Review Downloads' panel composition, some result-row metadata density and some
header/spacing details still differ from the supplied layouts. These should not
be described as exact matches. The source references remain the authority for
further layout refinement; no extra feature is approved by this review.

Fake CRC/integrity, drive-health, sample provider data and unsupported badges
remain excluded. No personal database/media changes or installer build occurred.

## Validation

Full regression suite: **572 passed**. The additional high-contrast calendar
construction check also passed. Focused checks cover cumulative ratings and
clear/lower behaviour, shared Add/Edit values, flat Details controls, rendered
yellow fill, calendar badge geometry, transparent release content and real
progress visibility. The publication guard and whitespace checks passed.
