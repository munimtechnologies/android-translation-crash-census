# Pre-registration: script-coded gettext catalogs (zh_Hans, zh_Hant, sr_Latn) in LINGUAS

linguas-script census PREREG v1. Written 2026-11-11, before the census job reads any repository.
Made with AI agents working for MV2 of Munim, Inc. (mv2@munimtech.com). Code: Apache-2.0. Text
and data: CC BY 4.0.

## The question

Translation platforms such as Weblate name Simplified and Traditional Chinese `zh_Hans` and
`zh_Hant` (and Latin-script Serbian `sr_Latn`). Linux programs don't look catalogs up by those
names. glibc's gettext and Python's `gettext` module start from the user's locale name, of the form
`language[_territory][.codeset][@modifier]` (for example `zh_CN.UTF-8` or `sr_RS.UTF-8@latin`),
and try that name and shorter forms of it (`zh_CN`, `zh`). No locale puts a script where the
territory goes. So a catalog that Meson or autotools installs as
`share/locale/zh_Hans/LC_MESSAGES/<domain>.mo` is found only when the user sets `LANGUAGE=zh_Hans`
by hand. Chinese users of the app see English, unless the app also ships a catalog under a
POSIX-style name of the same language (`zh_CN`, `zh_TW` or plain `zh`).

This is known case by case: Weblate issue #2559 (2019), Learn6502 #182, Vanilla-OS first-setup
#423, Luanti #17597 and #17598 (2026), and Warehouse #243. We found no count across a population of
apps, and no lint check that flags these names before release. l10n-guard 0.21.1's rename advice
for LINGUAS spellings is wrong for names with a script, which this census also feeds.

## Stage M: does the mechanism hold? (run first, inside the job container)

Before any repository is read, the job compiles one-message catalogs named `zh_Hans`, `zh_Hant`,
`sr_Latn` and the controls `zh_CN`, `zh_TW`, `sr@latin`, `pt_BR`, each alone in its own locale
tree. It generates the locales `zh_CN.UTF-8`, `zh_TW.UTF-8`, `zh_HK.UTF-8`, `zh_SG.UTF-8`,
`sr_RS.UTF-8@latin` and `pt_BR.UTF-8` with `localedef`. Then it asks which catalog each lookup
reaches with only `LANG` set (no `LANGUAGE`), using glibc's `gettext` program (M1) and Python's
`gettext.translation(..., fallback=True)` (M2).

- **M1 (glibc) and M2 (Python)** each HOLD when (a) no script-coded catalog is reached from any of
  the six locales, (b) `zh_CN`, `zh_TW`, `sr@latin` and `pt_BR` are each reached from their own
  locale, and (c) with `LANGUAGE` set to the script code, each script-coded catalog is reached,
  which shows the catalog itself works and only its name is the problem.
- M1 is NOT TESTABLE if any of the six locales fails to generate. Both are NOT TESTABLE if a
  catalog fails to compile.
- If M1 or M2 FAILS, the census numbers below are still reported, but only as counts of names.
  We will not claim these catalogs never load.

## Population (the same frame as the linguas census of 2026-11-09)

Every app in Flathub's appstream list on the day the job runs. Its repository comes from
`vcs_browser`, else `homepage`, on github.com, codeberg.org, bitbucket.org, git.sr.ht or a known
GitLab host. Repositories are deduplicated. Each is read at HEAD with a depth-1, blob-less clone.
A **governed directory** is an own (not vendored) directory holding `LINGUAS` and at least one
`.po` file whose build reads LINGUAS: a `meson.build` there calls `gettext(` without `languages:`
(meson), or `configure.ac`/`configure.in` uses gettext or intltool macros (autotools).
Meson reads LINGUAS skipping `#` lines; autotools treats `#` as a comment anywhere.

## Definitions

- **Script-coded code:** a word in a governed LINGUAS with an ISO 15924 script code after `_` in
  any case (`zh_Hans`, `zh_Hant`, `sr_Latn`, `zh_Hant_HK`). Names with `-` are counted separately
  (exploratory; l10n-guard already flags them). `de_FORM` and other non-script parts don't count.
- **Flagged repository:** a governed repository whose governed LINGUAS lists at least one
  script-coded code.
- **Lost catalog:** a listed script-coded code with no listed POSIX-style code of the same language
  (`zh_Hans` next to `zh_CN`, `zh_TW` or `zh` is not lost). This is conservative: a `zh_Hant`
  next to only `zh_CN` is still wrong for Taiwan users, but it doesn't count.
- **Substantive:** at least half of the catalog's non-header entries are translated and not fuzzy
  (up to 10 lost catalogs read per directory).

## Predictions

- **G (gate):** at least 1,000 repositories read and at least 150 governed. If G fails, P1-P5 are
  NOT TESTABLE.
- **P1:** between 2% and 15% (inclusive) of governed repositories are flagged.
- **P2:** at least half of the flagged repositories have at least one lost catalog. NOT TESTABLE
  with fewer than 4 flagged repositories.
- **P3:** governed repositories whose Flathub metadata names a Weblate translate URL are flagged at
  a higher rate than the other governed repositories. NOT TESTABLE if either group has fewer than
  20 repositories or fewer than 4 are flagged.
- **P4:** at least 75% of listed script-coded codes are Chinese (`zh_*`). NOT TESTABLE below 4
  codes.
- **P5:** at least 75% of lost catalogs whose content could be read are substantive. NOT TESTABLE
  below 4.
- **H (hand check):** the job picks one lost catalog with a `.po` file from each of the first 12
  flagged repositories that have one, in sha256 order of `linguas-script census v1|<repo>`. A person or agent
  then checks each at the recorded commit. It counts as **real** only if (1) the `.po` file holds a
  real translation into that language and script, not English copies or a template, (2) the build
  installs it under the script-coded name (nothing in `po/meson.build`, the root `meson.build`, the
  Flatpak manifest or the app's own locale code renames it or sets `LANGUAGE`), and (3) the repo
  isn't archived. H HOLDS with at least 10 real of 12. With n between 4 and 11, it holds if
  6 * real >= 5 * n. Below 4 it is NOT TESTABLE. Labels go in `labels.csv` with a note each.

## What we already know (stated so it isn't mistaken for a result)

- An earlier check of 20 hand-picked repositories (lingcheck, 2026-11-10) listed `zh_Hans` in the
  LINGUAS of marhkb/pods and flattool/warehouse (also `zh_Hant` in Warehouse). These two are the
  job's pipeline controls; they are in the population too.
- The 2026-11-09 linguas census listed `zh_Hant` twice among `.po` files left out of LINGUAS. It did
  not record which codes are listed, so it gives no count for this question.
- MV2's own pull request marhkb/pods#1054 (2026-11-10) added `zh_Hant` to Pods' LINGUAS. If M1
  holds, that catalog doesn't load on a default zh_TW system either, and we'll say so on that pull
  request.
- No population count was computed before this file was written.

## After the job

Results are reported in `linguas-script/RESULTS.md` against these predictions, with negatives
first, deviations listed in `DEVIATIONS.md`, and the job's outputs (`mechanism.json`,
`catalogs.csv`, `lost_files.csv`, `sample.csv`, `summary.json`) published unchanged. If M1 and H
hold, the next steps are an l10n-guard check (`linguas-script-code`, pre-registered separately)
and a small number of issues to affected projects, one per day, saying that the work was made with
AI agents.
