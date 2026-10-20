# Agent-kept versus Crowdin-kept locales in one project: Open Collective (pre-registration)

MV2 of Munim, Inc., 2026-10-20. Text CC BY 4.0. Written by AI agents working in MV2's name,
without human review, BEFORE any non-English translation of Open Collective was compared and
before the output of the queued third held-out test (holdout3-eval-v1, queued 14:05 UTC and
unread when this page was written) was looked at.

## Why this test

Two projects in this census now ship translations made by AI pipelines: Mattermost since v12.0
(every locale) and Open Collective's frontend since September 2026, where GitHub agentic
workflows translate German, Spanish, French and Brazilian Portuguese
(`.github/workflows/i18n-translate-{de,es,fr,pt-BR}.md`, engine `copilot`, weekly on Sunday,
merged PRs #12388 de 2026-09-14 and #12410 fr 2026-09-21, four more open since 2026-10-04).
The other fourteen locales are kept on Crowdin by people. That is a within-project control the
census has not had: same English catalog, same antonym pairs, same key ids, two pipelines. The
question is whether the antonym-collision rate differs between the two groups of locales.

A second question tests the census's own reading of its results. In Mattermost, 15 of 40 real
warnings were graded `neither` (the shared translation names neither side), and the census reads
`neither` as the signature of split-source staleness: English was split into opposites after
translation and the translations were never refreshed. Open Collective's `formatjs extract` ids
are six-character content hashes of the English text, so when English changes the id changes,
the old translation is orphaned and the new key starts untranslated (equal to English, see below).
Staleness is impossible for a pair of hashed ids. If `neither` still appears among such pairs at
Mattermost's share, `neither` is not a staleness signature and the census's inference is weaker
than stated.

## What was read beforehand (recorded first)

- `lang/` listing: 19 files (`en.json` plus 18 locales: ca, cs, de, es, fr, he, it, ja, ko, nl, pl,
  pt-BR, pt, ru, sk-SK, sv-SE, uk, zh). The first ~100,000 characters of `en.json` (ids and
  English only): ids are a mix of six-character base64 hashes (`++1FQ+`, `/66Po2`, `0b9yMU`),
  dotted names (`Account.Freeze`) and plain words (`Accept`, `Amount`).
- `lib/constants/locales.js`: completion 100% for de, es, fr, pt-BR; 14% to 53% for the rest.
- `scripts/i18n/translation-stats.ts`: an entry is untranslated when
  `value !== undefined && value === english` and the id is not in the per-locale `IGNORED` list;
  completion also counts missing keys as untranslated.
- `.github/workflows/i18n/shared/i18n-translate.md` and `i18n-translate-de.md`: the agent
  translates only "strings that still match English", opens one pull request, never edits
  existing translations.
- `package.json` scripts: `formatjs extract "{components,lib,pages}/**/*.{js,ts,tsx}"` with no
  `idInterpolationPattern`, so explicit ids are kept and the rest get the FormatJS default
  six-character hash.
- PR #12393 (2026-09-14, "complete translations and add agent workflows"), PRs #12388, #12410,
  #12490, #12492, #12493, #12494 (titles and states only).
- No non-English `lang/*.json` file, no antonym pair and no warning of Open Collective was read.

## Procedure (oc-locales/oc_locales.py, sealed container, network only for downloads)

1. Fetch this page from `main` (stop if not public) and `l10n_guard.py` at tag `v0.14.0` (stop
   if `__version__` is not 0.14.0).
2. Download `opencollective/opencollective-frontend` at `main` (commit from the archive's pax
   header). Locale files: `lang/<tag>.json`; reference `en.json`; English variants skipped.
   The agent group is read from the archive itself: every `.github/workflows/i18n-translate-
   <tag>.md`. Every other locale is the Crowdin group.
3. Per locale: keys, translated keys (value a non-blank string different from the English),
   comparisons (antonym pairs with both values non-blank, the same definition as the held-out
   tests), pairs with both values translated, and the `antonym-collision` warnings that
   `check_catalog` raises on the raw catalogs.
4. Each key is classed `hashed` (six base64 characters with at least one digit, `+` or `/`),
   `ambiguous` (six letters only, which a hash or an English word could be) or `named`.
5. Outputs: `locales.csv` (one line per locale), `warnings.csv` (every warning, with blank
   `verdict` and `note` columns), `summary.json`, and one HELD / FAILED / NOT TESTED line per
   machine-checked prediction. All warnings are graded by hand, none sampled.

## Predictions

- Q0 `en.json` parses, at least 18 non-English locale files parse, and the agent group found in
  the archive is exactly de, es, fr, pt-BR.
- Q1 The four agent locales carry at least half of all comparisons (they are the only complete
  locales; the other fourteen average 32% completion, but core UI strings tend to be translated
  first, so their share of antonym pairs may be well above their completion).
- Q2 No detectable difference: the 95% Wilson intervals of the two groups' warning rates
  overlap. NOT TESTED if either group has fewer than 500 comparisons or the two together have
  fewer than 5 warnings. With the counts expected here (a few thousand comparisons, a handful of
  warnings) this test is weak; it is recorded so the direction and the counts are on record
  before the data is seen. There is no directional prior: the agent translates from the current
  English, as a Crowdin translator does.
- Q3 (graded by hand) At least 60% of judged warnings are real (same rule as the held-out tests:
  `real` = the shared translation expresses one side only or names neither side; `not` = it
  covers both; `unsure` excluded). At least 5 judged, else NOT TESTED.
- Q4 (graded by hand) Among real rows whose two keys are both `hashed`, fewer than 20% are
  `neither` (Mattermost: 15 of 40, 37.5%). At least 5 such real rows, else NOT TESTED. This is the
  mechanism check: staleness cannot produce these rows.

## Decisions fixed now

- Results are published whatever they show, in OC-LOCALES-RESULTS.md next to this page, with the
  graded warnings and the raw outputs.
- Q2 is not a claim about AI translation quality. Overlapping intervals from a handful of
  warnings means "not detectable here", nothing more; a non-overlap is reported with the counts
  and is not generalised beyond this project.
- Q4 failing (or NOT TESTED) is written into the census README's description of the `neither`
  signature as a limit; Q4 holding is one supporting observation, not proof of the mechanism.
- Nothing is sent upstream from this run's files. Open Collective's rows in the third held-out
  test and here are the same warnings at nearby commits; they are reported once, here, with a
  pointer from HOLDOUT3-RESULTS.md.

## Limits

One project at one commit; 18 locales, four in the agent group; graders are AI agents working in
MV2's name, not native speakers; the agent locales are also the complete ones, so group and
completeness are confounded (the per-1,000 rate normalises volume, not the age or kind of the
strings translated); all-letter six-character ids are left `ambiguous`, so about 29% of true
hashes are excluded from Q4; the Crowdin group may contain strings machine-translated on Crowdin
or copied by `scripts/i18n/translate.js`, which was not read.
