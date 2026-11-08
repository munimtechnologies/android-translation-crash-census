# Results: l10n-guard 0.19.0 locale-config check (pre-registered)

Graded 2026-11-08. Pre-registration: [PREREG.md](PREREG.md) (marker "l10n-guard 0.19.0 locale-config
PREREG v1", sha256 `1450ada3...0ba34`). The first build job stopped before any data was read and was
re-run unchanged in its predictions; see [DEVIATIONS.md](DEVIATIONS.md). Job outputs are in
[v2/](v2/), byte for byte as the job wrote them. The hand labels are kept apart in
[labels.csv](labels.csv). Made by AI agents working for MV2 of Munim, Inc.; labels were made by AI
agents reading the repositories through the GitHub and Forgejo APIs, not by the projects' maintainers.

## What was tested

Since Android 13 a user can pick a language for a single app, but Android offers only the languages
in the app's `locales_config.xml`. When that list is written by hand it drifts from the translations
the app ships. The new `l10n-guard locale-config <project>` command reports four things:

- **orphan**: a translation at least half done that the list leaves out (never offered);
- **phantom**: a listed language with no translated strings (offered, but shows the default language);
- **code**: a listed code that is not a language (`dk`);
- **tag**: a resource-folder spelling such as `pt-rBR` (reported, not graded).

## Verdicts (as pre-registered, unchanged)

| Prediction | Bar | Result | Verdict |
|---|---|---|---|
| R1: the 4 census rows found not real come out clean | every row read passes, at least 3 read | 4 of 4 clean | **HELD** |
| R2: the 12 confirmed census rows still get a confirmed finding | all but at most 1, at least 10 read | 12 of 12 | **HELD** |
| R3: none of the 17 orphans dropped by `localeFilters` is reported (MMRL, Flashy) | 0 reported | 0 reported | **HELD** |
| H1: share of held-out repositories flagged | between 3/5 and 9/10, at least 60 read | 82 of 96 (85%) | **HELD** |
| H2: sampled flagged repositories with a real finding | at least 13 of 16 | **14 of 16** | **HELD** |
| H3: checked findings that are real | at least 3/4 | **31 of 36** (86%) | **HELD** |

With the four borderline labels flipped to "not real" (ToDont `la`, AliasVault `ca` and `bg`), H2 is
13 of 16 and H3 is 28 of 36 (78%): both still hold, H2 exactly at its bar.

All 17 existing test modules passed before and after the change, and the 25 new tests passed.

**Release rule** (pre-registered): release 0.19.0 if R1, R2 and R3 hold and at least 12 of the 16
sampled repositories have a real finding. All three held and 14 of 16 did, so 0.19.0 is released.

## The five findings that were not real

They fall into two kinds, and both are gaps in the method, not chance:

1. **Translations that don't live in Android's `res/` folders (4 findings, 2 repositories).**
   - SiYuan (`fr`, `ko`, `de` phantoms): the per-app language is handed to SiYuan's own engine,
     whose web interface ships those languages. Android's `res/` has only Russian and Chinese
     because the interface isn't there.
   - Server Box (`az` phantom): a Flutter app. Its translations are `lib/l10n/app_*.arb` files, and
     its list says it mirrors them. `app_az.arb` exists.

   A phantom warning is only meaningful when the app's text really comes from `res/`. Flutter, React
   Native and web-view apps keep it elsewhere.
2. **English copies counted as translations (1 finding, plus 2 borderline).** AliasVault's
   `values-fa/strings.xml` holds the English text unchanged (the same file as `values-cs`), yet the
   message said "86 of 87 strings translated". The check counts strings that are *present* in a
   folder, not strings that *differ* from the default. Its `values-ca` and `values-bg` are real but
   thin translations (about 8 and 17 of 87 strings), and are labelled real-but-borderline.

## Exploratory (not pre-registered)

- Across the 96 held-out repositories the job reported 253 orphan, 428 phantom and 40 tag findings.
  Phantoms are the most common, so the method gap in point 1 matters most there.
- Fixes planned for the next version, to be tested on a fresh sample before release: count only
  strings that differ from the default when sizing a translation, and skip the phantom check
  (or say why) when a project ships its interface text in another catalog format (`.arb`, i18next
  JSON, gettext) or through a web view.
- Prior art: Android Lint's `UnusedTranslation` check (since AGP 7.4) already warns about
  translated folders that the locale config leaves out, but only as a warning during a Gradle or
  IDE lint run. What is new here is phantoms, non-language codes, awareness of `localeFilters`, and
  a check that needs no Gradle build.

## Files

- [labels.csv](labels.csv): one row per sampled finding, with label, borderline flag and the evidence.
- [v2/summary.json](v2/summary.json), [v2/sample.csv](v2/sample.csv), [v2/findings.csv](v2/findings.csv),
  [v2/regression.csv](v2/regression.csv), [v2/report.txt](v2/report.txt),
  [v2/build-summary.json](v2/build-summary.json): job outputs, unchanged.

Licence: text and data CC BY 4.0; code Apache-2.0.
