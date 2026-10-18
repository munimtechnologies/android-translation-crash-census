# crash_age 0.1.0 results: crashing translations are old, and most were never caught

MV2 of Munim, Inc. Made with AI agents; every number below comes from the job's output, and the
hand checks were done by reading the commits on the web. Licence: this text and the CSV/JSON files
CC BY 4.0; code Apache-2.0.

The question, method and six predictions are in [PREDICTIONS.md](PREDICTIONS.md), published before
the first run. The job (`crash-age-v1`) ran on 2026-10-17 from 18:11 to 18:19 UTC: tests passed,
then [crash_age.py](crash_age.py) walked the history of every strings.xml file behind the 453
rows of [callsites/findings.csv](../callsites/findings.csv) (360 "crash", 93 "crash-if-text") in
118 repositories. Ages are counted to 2026-10-17 05:13 UTC.

Output: [ages.csv](ages.csv) (one line per row), [repos.csv](repos.csv),
[crash_age.json](crash_age.json), [crash_age.md](crash_age.md).

## Headline

A translation that makes `String.format` throw had been in its repository for a **median of
745.5 days (about two years)** when the census read it. Two thirds (232 of 353 dated rows) were
older than two years; only 25 had arrived in the last 90 days. Per repository the picture is the
same or older: the median of the 93 per-repository medians is 1,137 days. These strings are not
fresh mistakes waiting for the next review; they shipped and stayed.

## The predictions, graded

| | Prediction | Result | Verdict |
|---|---|---|---|
| A1 | median age of dated crash rows >= 365 days | 745.5 days (353 rows) | **held** |
| A2 | at least half arrived through a translation platform's commit | 186 of 353 (52.7%) | **held, narrowly** (see below) |
| A3 | Weblate is the most common pipeline, ahead of direct commits | direct 167, Weblate 59, Transifex 57, translatewiki.net 32, Crowdin 26, POEditor 7, Localazy 4, Lokalise 1 | **failed** |
| A4 | at least 5% were gone at some point and came back | 7 of 353 (2.0%) | **failed** |
| A5 | at least 80% of crash rows are dated | 353 of 360 (98.1%) | **held** |
| A6 | median age of rows the census calls "formatted" >= 180 days | 733.1 days (226 rows) | **held** |

"Dated" means dated exactly (234 rows) or as a lower bound (119 rows, where the text has been
there since the file's first version at that path, so the true age may be greater). Using exact
dates only, the median is 733.1 days, so A1 does not depend on the lower bounds.

## What the numbers hide (read before quoting A2 or A3)

- **One sync carries the Transifex count.** 54 of the 57 Transifex rows are a single ownCloud
  Android commit (`9579763`, 2024-10-14) that brought one Uyghur file. Without it, platforms
  account for 132 of 299 dated rows (44.1%), and A2 would fail. A2 held, but only because of
  that one file.
- **Lower bounds lean "direct".** For a lower-bound row the commit classed is the file's first
  version, which is often the developer adding the file. Of the 119 lower-bound rows, 83 are
  "direct"; of the 234 exactly dated rows, 84 are "direct" and 150 (64.1%) came through a
  platform.
- **"Direct" includes things that are not hand edits.** It means the commit (or, for a merge,
  the merged commits touching the file) does not name a platform. In Cashiro, 22 of its 25
  crash rows trace to one commit by the maintainer, `701dd18` (2026-07-08), titled "feat:
  multilingual translations done by bling translation api": machine translation through an API,
  classed "direct". In Tella, a squash merge of a develop branch that had folded in Lokalise
  translation pull requests is also "direct".
- So A3 fails clearly (direct commits outnumber every platform), but "direct" is an upper bound
  on hand-made commits and the platform share is a lower bound.

## Hand checks

Six introducing commits, opened on GitHub:

| Row | Commit | What it is | Class given | Right? |
|---|---|---|---|---|
| Wikimedia Commons, my, `share_license_summary[one]` | `197855a` | "Localisation updates from https://translatewiki.net." by the translatewiki bot | translatewiki | yes |
| Money Manager Ex, pt-rBR, `enter_budget_value` | `e66aca3` | merge of the `l10n_crowdin_translations` pull request, one file | crowdin | yes |
| APK Explorer & Editor, cs, `signing` | `f7493e5` | maintainer commit "res: Updated translations and language switch"; its diff shows `Přihlašování %s…` becoming `Přihlašování% s…` | direct | yes by the rule; the diff confirms this commit brought the broken text |
| Cashiro, tk, `percentage_format` | `bdf7ab6` | maintainer commit "chore(localization): add multi-language new translations", 70 files | direct | yes |
| Retro Music Player, te-rIN, `could_not_scan_files` | `b74b480` | merge of a feature pull request (#1226), 328 files | direct | not settled: the page was cut off before the locale files |
| Tella, ksw, `Vault_Encryting_SheetText` | `e70aa4f` | squash merge "merge develop into main (#484)", which folded in Lokalise sync pull requests | direct | by the rule yes, in meaning probably Lokalise |

The seven crash rows that were gone and came back (A4):

- **APK Explorer & Editor, cs `signing`**: present from 2021-04, then replaced, then back in
  2023-08 in the maintainer's translation update above.
- **Cashiro, tk `percentage_format`**: first in the machine-translation commit of 2026-07-08,
  gone, then back on 2026-08-16 in another bulk translation commit.
- **Wikimedia Commons, my `share_license_summary[one]`**: first in 2019-06, back in 2024-10 through
  a translatewiki.net sync.
- **Money Manager Ex, pt-rBR `enter_budget_value`**: first in 2025-04, back in 2026-02 through a
  Crowdin merge.
- **Retro Music Player, fa-rIR `label_more_from`** (Crowdin, 2021-09 then 2021-10) and **te-rIN
  `could_not_scan_files`** (2020-04, back in 2022-01 through a feature merge).
- **Tella, ksw `Vault_Encryting_SheetText`**: first in 2022-09; the file's history shows a
  "Removed unused languages" commit on 2026-04-16 and the text back on 2026-06-08 in the squash
  merge above. GitHub's file history is not first-parent, so this order is likely, not certain.

In five of the seven, the text came back in a platform sync or a bulk translation commit. The
job does not say why each one disappeared, and we did not check every intermediate version.

## Rows the job could not date

- **Repository failed (2 rows)**: git.server47.de/jens/Automation could not be cloned from the
  sandbox.
- **Not found (5 rows)**: four Wikimedia Commons `about_improve` rows (b+nds+NL, haw, hrx, hsb)
  and one NewPipe row (in, `sign_in_confirm_not_bot_error`). The census's text was not matched in
  the newest version the job read. Why: these five translations hold escaped link markup, which crash_age 0.1.0 matched with an older text rule; see [NOT-FOUND.md](NOT-FOUND.md).

## crash-if-text rows (not scored)

93 rows, all dated (55 exactly). Median age 469.5 days; per-repository median 396.3 days
(31 repositories); 67 direct, 17 Crowdin, 5 Weblate, 4 Transifex; 7 came back.

## Limits

- Rows cluster heavily by repository and commit (crash rows: ownCloud 56, Wikimedia Commons 36,
  Cashiro 25, Tella 19). Treat the row medians as describing these 118 repositories, not Android apps in
  general; the per-repository median is given beside each.
- Age is how long the exact text has been in the repository's main history, not how long users
  had it: release dates and app store builds were not checked.
- Pipeline classes come from commit metadata only (author, committer, subject, merged commits).
  They were checked by hand for six commits, with one likely miss (Tella).
- The sample is the census's own: open-source Android apps with findings, not a random sample.

## Prior art

A search on 2026-10-17 found studies of i18n layout bugs in Android apps (Escobar-Velasquez et
al., ICSME 2020) and of Android crashes in general, and many single-project issues about
crashing translations, but no measurement of how long format-crashing translations stay in
repositories, how they arrive, or how often they come back. This is, as far as we found, the
first.
