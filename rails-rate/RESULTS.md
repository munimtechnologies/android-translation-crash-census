# Results: how often Rails translations break `%{name}` interpolation

Graded 2026-10-18 against the predictions in [PREREG.md](PREREG.md), which was published
(commit 1d071b3, 18:00 UTC) before the job ran (20:09-20:12 UTC). Made by MV2 of Munim, Inc.,
with AI agents. Text and tables CC BY 4.0; the CSV files next to this page are CC BY 4.0 too.

## What ran

Compute job `rails-rate-v1` ran `rails_rate.py` 0.1.0 (PyYAML 6.0.2, git 2.47.3) once, in a sealed
container, after its 15 offline tests passed. The population is every git submodule pinned in
[Real World Rails](https://github.com/eliotsykes/real-world-rails) at commit `c5e6e6e1`: 214
repositories (171 apps, 43 engines), each at one fixed commit. For each one only `config/locales/`
at that commit was fetched.

| | Count |
|---|---|
| Pinned repositories | 214 |
| Fetched | 209 (5 failed: `askthem`'s commit is no longer on the remote; `cartodb`, `heaven`, `hound` and `prison-visits` now need a login, so they are gone or private) |
| YAML files under `config/locales/` | 4,268 |
| Loaded by PyYAML | 4,252 (16 load errors, listed below) |
| Repositories with English and at least one other locale compared | 69 |
| (repository, locale) pairs compared with English | 1,525 |
| Strings compared | 1,557,839 |
| Strings whose English has a placeholder | 235,218 |
| Strings with at least one error | 2,224 (0.95% of placeholder strings) |

Load errors: three ministryofjustice files with a duplicate YAML anchor (`claim-for-crown-court-defence`
twice, `defence-request-service`), eleven `fat_free_crm` files with a tag PyYAML's safe loader doesn't
construct (`tag:yaml.org,2002:yaml`), one `inch_ci-web` file with an unknown escape in a quoted scalar,
and `communityengine`'s `es-MX.yml` with a custom `!Gracias` tag. They are in `files.csv` with the
message.

## Predictions

| | Prediction | Result | Value |
|---|---|---|---|
| P1 | Fewer than 2% of compared (repository, locale) pairs have a look-alike placeholder error | HELD | 7 of 1,525 (0.46%) |
| P2 | Every look-alike placeholder error is in a Chinese, Japanese, Korean or Arabic-script locale | HELD | 135 errors; none outside |
| P3 | The share of placeholder strings with a look-alike error is higher in those locales than in all others | HELD | 111 of 31,067 vs 0 of 204,151; one-sided Fisher p = 2.2e-98 |
| P4 | Missing-placeholder errors outnumber look-alike errors at least 10 to 1 | HELD | 2,446 vs 135 |
| P5 | At least 95% of the YAML files under `config/locales/` load with PyYAML | HELD | 4,252 of 4,268 (99.6%) |
| P6 | At least 180 of the 214 pinned commits fetch, and at least 40 repositories have a translation compared with English | HELD | 209 fetched; 69 compared |
| P7 | "Dropped" is the most common kind of placeholder error | HELD | 1,809 dropped; next is renamed, 460 |

All seven held. The predictions were conservative on purpose (P1 allowed up to 2%, P4 only 10 to 1)
and the margins are large, so the result says less about the exact rates than about the direction:
the look-alike pattern seen in nine other formats holds in Rails too.

## What the errors are

Every placeholder error, by kind. "Error" means the English placeholder is gone from a form where it
has to be; "warning" means a placeholder missing from a `zero`, `one` or `two` plural form, or a
placeholder the translation adds (which raises `I18n::MissingInterpolationArgument` only if the app
doesn't pass it).

| Kind | What the translation has instead of `%{name}` | Errors | Warnings |
|---|---|---|---|
| dropped | nothing | 1,809 | 1,766 |
| renamed | another `%{...}` the English doesn't have | 460 | 25 |
| look-alike percent | `％{name}`, `٪ {name}` | 135 | 6 |
| no percent | `{name}`, `{{name}}` | 110 | 8 |
| spaced | `% {name}`, `%{ name }` | 62 | 1 |
| other syntax | `${name}`, `%(name)`, `%name%` | 4 | 1 |
| Ruby hash | `#{name}` | 1 | 0 |
| look-alike brace | `%｛name｝` | 0 | 0 |
| extra placeholder | (a `%{name}` the English lacks) | | 454 |

So 2,581 error-level problems in 2,224 strings. Dropped placeholders are 70% of them. Some of those
are deliberate ("one file" instead of "%{count} file"), which is why the pre-registration counted
them separately from the look-alikes, whose only explanation is a typing or tooling slip.

## Where the look-alikes are

All 135 look-alike errors sit in seven (repository, locale) pairs, out of the 172 compared pairs whose
locale is Chinese, Japanese, Korean or Arabic-script, and in none of the 1,353 other pairs.

| Repository | Locale | Look-alike errors | Strings | Of the locale's placeholder strings | Form |
|---|---|---|---|---|---|
| loomio | ar | 119 | 95 | 386 (25%) | `٪ {name}` (Arabic percent sign U+066A, then a space) |
| whitehall (GOV.UK) | ja | 11 | 11 | 13 (85%) | `％{name}` (fullwidth U+FF05) |
| camaleon-cms | zh-CN | 1 | 1 | 37 | `％{d}` |
| openstreetmap-website | ja | 1 | 1 | 387 | `％{oauth2}` |
| sharetribe | ja | 1 | 1 | 483 | `％{service_name}` |
| wiki_edu_dashboard | sd | 1 | 1 | 13 | `٪{query}` |
| hyrax (engine) | zh | 1 | 1 | 113 | `％{work_title}` |

Six warnings are the OpenStreetMap Arabic strings already described in
[RAILS.md](../lookalike-percent/RAILS.md): a `٪ {name}` next to the real `%{name}`, so the value is
shown and the stray text is cosmetic. Every one of the 141 is in `problems.csv` with the English and
the translation.

Three things stand out:

- **Loomio's Arabic file is the largest percent-sign case the census has found.** 95 of its 386
  placeholder strings (a quarter) write every placeholder as `٪ {name}`: the Arabic percent sign and a
  space. A sample, `common.in_x_days`: English `in %{x} days`, Arabic `في٪ {x} يوم`. Poll e-mails,
  notifications, the "people have voted" line (`٪ {nom}`, `٪ {dnom}`, `٪ {pct}`), the account-merge
  e-mail (`٪ {source_email}`, `٪ {target_email}`): all show the raw text instead of the value. The
  Arabic percent sign followed by a space is how Arabic text sets a percentage, and it is also what
  machine translation produces from `%{x}`; we did not check how Loomio's Arabic was made, only
  that the result is this.
- **Whitehall's Japanese file is almost entirely broken:** 11 of its 13 placeholder strings. It is a
  small file (174 strings), and the English placeholders in it are the ones GOV.UK uses for
  organisation names, countries and links.
- **Single slips everywhere else.** The other five cases are one string each, in files of 37 to 483
  placeholder strings, the same picture as in Android, Qt, .NET, Laravel and Symfony: a rare typing
  slip, found only in Chinese, Japanese and Arabic-script files.

## Pairs with the most error strings

The 12 compared pairs with 20 or more strings in error (all kinds). The full list is `locales.csv`.

| Repository | Locale | Placeholder strings | Error strings | Note |
|---|---|---|---|---|
| loomio | ar | 386 | 256 | 95 look-alike, 218 missing (overlapping strings) |
| discourse | be | 405 | 111 | dropped and renamed |
| discourse | sw | 652 | 62 | |
| wiki_edu_dashboard | qqq | 57 | 53 | `qqq` is translatewiki.net's message-documentation pseudo-locale, not a translation; it should have been excluded and inflates the totals by 53 strings |
| discourse | fa_IR | 966 | 29 | |
| sharetribe | fi | 673 | 29 | |
| sharetribe | vi | 365 | 27 | |
| sharetribe | es-CL | 176 | 26 | |
| rubygems.org | zh-CN | 96 | 23 | |
| discourse | zh_TW | 828 | 21 | |
| sharetribe | da-DK | 576 | 21 | |
| sharetribe | ka | 404 | 21 | |

## Exploratory (not predicted)

- The group rate: 7 of the 172 Chinese, Japanese, Korean and Arabic-script pairs (4.1%) have a
  look-alike error, against 0 of 1,353 others. By strings, 111 of 31,067 placeholder strings in the
  group (0.36%) against 0 of 204,151.
- Korean is in the group by definition but had no case here, as in every earlier format.
- **The two big cases are not open bugs today.** Checked on 2026-10-18 after the run: Loomio's
  `master` has no Arabic locale any more (its `config/locales/` lists 25 locales, `ar` not among
  them), and Whitehall's `main` keeps only `en.yml` and `cy.yml`. Both files were dropped with their
  look-alikes in them, so there is nothing to report upstream; the snapshot caveat below is real.
- `24pullrequests` at its 2024 commit has the same one dropped placeholder
  (`homepage.involved.take_a_look`, `%{contributing_path}`) in each of 19 locales. Its maintainers
  later ran i18n-tasks on the project (pull request #5085); this snapshot predates that.
- `canvas-lms` (317) and `catarse` (180) have many "collisions": the same key defined with different
  values in two files of one locale. The study keeps the later file, as I18n's load path would, but
  the app may load them in another order.

## Limits

- **Snapshot, not today.** The commits are from 2024 or earlier (Real World Rails was archived in
  2026). Some of these strings have been fixed since; some repositories are gone. The numbers describe
  the pinned snapshot.
- **Files, not screens.** A key no view uses still counts. A placeholder the app passes but the English
  never uses makes an "extra" harmless. Dropped placeholders can be deliberate. Nothing was run.
- **`qqq` was not excluded** (see the table above): 53 of the 2,224 error strings are documentation,
  not translation. The look-alike counts are unaffected (`qqq` has none).
- **Every file under `config/locales/` was merged**, recursively, into its locale. Rails' default load
  path reads only the top folder; most apps that nest add the rest, but not all.
- **PyYAML's `safe_load` is not Psych.** 16 files (0.4%) did not load; Rails loads some of them.
- **The rules are the pre-registered ones**, written independently of l10n-guard 0.10.0's `rails`
  kind but to the same specification, and they share any blind spot of that specification (for
  instance, a translation that writes `%{Name}` for `%{name}` counts as renamed, and a `%<name>d`
  for `%<name>s` counts as correct).
- **Large apps dominate string totals.** Discourse (191 locales), Mastodon (93), Diaspora (91) and
  OpenStreetMap (104) are most of the 1,525 pairs. The per-pair and per-repository tables above are
  the fairer view.

## Prior art

i18n-tasks' `check-consistent-interpolations` finds these problems in one project at a time, and
recent pull requests report 4 to 20 per project (24pullrequests #5085, Solidus #6655). Searches on
2026-10-18 found no measurement across many Rails apps, and no earlier note that the look-alike
percent sign in Rails files is confined to Chinese, Japanese and Arabic-script locales.

## Files

- `summary.json`: totals, counts by kind, and the graded predictions, as written by the job.
- `population.csv`: the 214 submodules (path, URL, pinned commit).
- `repos.csv`: one row per repository (fetched, files, loaded, English root, locales, compared,
  collisions, seconds, error).
- `files.csv`: one row per YAML file (loaded, locale roots, load error).
- `locales.csv`: one row per compared (repository, locale) pair with all counts.
- `problems.csv`: one row per problem (7,635 rows): repository, commit, locale, key, plural
  quantity, level, code, kind, placeholder name, what was seen instead, English, translation.

The code is [rails_rate.py](rails_rate.py) with [test_rails_rate.py](test_rails_rate.py); the job
ran `python -B rails_rate.py --out-dir /out/rails-rate --workers 6` and took 1.1 minutes after the
fetches.
