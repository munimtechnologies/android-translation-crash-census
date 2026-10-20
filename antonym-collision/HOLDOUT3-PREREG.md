# Third held-out test of the antonym-collision check: five react-intl projects (pre-registration)

MV2 of Munim, Inc., 2026-10-20. Text CC BY 4.0. Written by AI agents working in MV2's name,
without human review, BEFORE any translation of the five projects was compared.

## Why this test

The FormatJS test ([FORMATJS-RESULTS.md](FORMATJS-RESULTS.md), l10n-guard 0.14.0 on Mattermost)
found that 21 of its 67 warnings were one defect: English had been split into two opposite
messages ("Convert to private" / "Convert to public") after the translations were made, and the
translations were never refreshed, so both keys still carry the old generic text in ten languages.
No placeholder or ICU checker can see this ("split-source staleness"). That is one project and one
pipeline. This test asks whether antonym collisions, and this generic-translation signature, show
up at a similar rate in other projects that use FormatJS / react-intl.

## Negative search for descriptor sources (recorded first)

The plan was a third test on more FormatJS `extract` ("descriptor") sources, the shape 0.14.0 was
written for (`{"id": {"defaultMessage": ..., "description": ...}}`). The committed English files of
the five react-intl projects below were read on 2026-10-20 (first 12 to 15 lines of each, plus the
folder listings):

| project | English file | shape |
|---|---|---|
| Mastodon | app/javascript/mastodon/locales/en.json | flat id -> string |
| BigBlueButton HTML5 client | bigbluebutton-html5/public/locales/en.json | flat id -> string |
| Strapi admin | packages/core/admin/admin/src/translations/en.json | flat id -> string |
| Umami | public/intl/messages/en-US.json | nested (label.*, message.*) -> string |
| Open Collective frontend | lang/en.json | flat hashed id -> string |

None is a descriptor file: projects commit the compiled or hand-kept catalog, not the extract
output. Fewer than three descriptor sources were found, so the descriptor follow-up is recorded as
a negative search, and the third held-out test uses these five flat catalogs instead. The check
itself (`json` kind) reads flat and nested catalogs since 0.12.0, so nothing in the tool changes.

## What was read beforehand

Only the folder listings (file names, counts) and the first 12 to 15 lines of each English file.
No warning, no antonym pair and no non-English translation of any of the five projects was looked
at before this page was committed. The guard is the released l10n-guard 0.14.0 (unchanged). Prior
art for the check is unchanged from [FORMATJS-PREREG.md](FORMATJS-PREREG.md): no public checker
compares translations of antonym pairs for identity.

## Procedure (holdout3/eval_holdout3.py, sealed container, network only for downloads)

1. Fetch this page from `main` (stop if not public) and `l10n_guard.py` at tag `v0.14.0`
   (stop if its `__version__` is not 0.14.0).
2. Download each project's default-branch tarball (commit recorded from the archive's pax
   header): mastodon/mastodon `main`, bigbluebutton/bigbluebutton `develop`, strapi/strapi
   `develop`, umami-software/umami `master`, opencollective/opencollective-frontend `main`.
3. Locale files: the JSON files in the folders above whose name is a language tag. Reference:
   `en.json` (Umami: `en-US.json`). English variants (en-GB, en-AU, ...) are skipped. Files that
   do not parse as JSON objects are counted as unparsed.
4. A comparison is one antonym pair (from `antonym_pairs` on the flattened reference) in one
   locale where both keys are translated and non-blank. Warnings are `check_catalog`'s
   `antonym-collision` problems on the raw catalogs, as the command line would raise them.
5. For each warned key pair, record whether each key appears as a quoted literal in the
   project's source files (`key1_used`, `key2_used`).
6. Outputs: `warnings.csv` (every warning, all projects), `sample.csv` (up to 40 warnings drawn
   with seed 150 from all projects pooled, with blank `verdict` and `note` columns),
   `summary.json`, and one HELD / FAILED / NOT TESTED line per machine-checked prediction.

## Predictions

- P0 Every reference parses, every project has at least 10 parsed non-English locale files, and
  the five together have at least 120.
- P1 At least 10,000 comparisons pooled across the five projects (the FormatJS test had 25,515
  on one project; Open Collective alone has only 18 non-English files).
- P2 The pooled warning rate is between 0.5 and 5.0 per 1,000 comparisons (earlier projects:
  1.01 to 3.08; Mattermost 2.63), and at least 3 of the 5 projects raise at least one warning.
- P3 (graded by hand from sample.csv) At least 60% of judged warnings are real defects; at least
  5 must be judged, else NOT TESTED. `real` = the shared translation expresses one side only, or
  names neither side clearly; `not` = it genuinely covers both keys; `unsure` is excluded.
- P4 (graded by hand) Among the rows judged `real`, at least 20% are `neither`: the shared
  translation names neither side (the split-source-staleness signature; 15 of 40 real rows in
  Mattermost). At least 10 real rows must exist, else NOT TESTED.
- P5 At least 80% of warned rows have both keys found as literals in source (dead keys would
  make a warning harmless; Mattermost: 40 of 40). Open Collective's hashed ids may be generated
  at build time rather than written in source: if fewer than half of its warned rows have both
  keys found, P5 is judged on the other four projects and its share is reported separately.

## Decisions fixed now

- Results are published whatever they show, in HOLDOUT3-RESULTS.md next to this page, with the
  graded sample and the raw outputs.
- P2 failing with 0 warnings everywhere is a negative result and changes no code. P2 failing above
  5.0 per 1,000: look for one systematic cause (a word class, one project) before grading.
- P3 holding: `real` rows become upstream candidates, after re-checking the current files and
  reading each project's translation policy (Mastodon and Open Collective use Crowdin,
  BigBlueButton uses Transifex, Strapi and Umami take pull requests; to be verified), and only
  once MV2's GitHub account is visible. P3 failing: the README records the precision; no word
  class is changed on these projects' evidence.
- P4 is a measurement of the staleness mechanism outside Mattermost; holding or failing, the
  share is reported with the rows behind it.
- Nothing is reported upstream from this run's files without re-checking the live files.

## Limits

Five projects at one commit each; graders are AI agents working in MV2's name, not native
speakers, and some locales will lack a competent reader (marked `unsure`); the 39 word classes
measure precision only, never recall; `neither` versus `opposite` is a judgement about the shared
translation, not a check of each project's git history, so the mechanism is inferred, not
observed; English variants are skipped, so a collision in en-GB would be missed.
