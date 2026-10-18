# Pre-registration: how often Rails translations break `%{name}` interpolation

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0. Written and published
**before** the run it describes. The run's results will be added next to this file, and the
predictions will not be edited.

## Question

Ruby on Rails apps keep their translations in `config/locales/*.yml`. Ruby's I18n fills
`%{name}` (and `%<name>s`) placeholders and nothing else. So a translation that drops
`%{count}`, writes it as `％{count}` or `% {date}`, or renames it `%{nombre}` shows the
wrong text. One that adds a `%{name}` the app doesn't pass raises
`I18n::MissingInterpolationArgument`. i18n-tasks (`check-consistent-interpolations`) finds
these one project at a time, and recent pull requests report 4 to 20 per project
(24pullrequests #5085, Solidus #6655). We found no measurement across many apps. This run
makes one, and tests whether the look-alike pattern seen in nine other formats (every
case was Chinese, Japanese or Arabic-script) holds in Rails too.

## Population and method (fixed before the run)

- **Population:** every application and engine pinned as a git submodule in
  [Real World Rails](https://github.com/eliotsykes/real-world-rails) at its last commit,
  `c5e6e6e1d9f74026ca3d7fad449998803dbba9af` (2024-07-21; the repository was archived in
  2026). Its `.gitmodules` lists 214 submodules (171 apps, 43 engines), each pinned to one
  commit. We didn't choose the sample, and it can't change.
- For each submodule, only `config/locales/` at the pinned commit is fetched (depth 1,
  blobless, sparse). Every `.yml`/`.yaml` file there is loaded with PyYAML 6.0.2
  (`safe_load` rules). Each top-level locale key (`en:`, `ja:`, `pt-BR:`) is merged into
  that locale, as I18n merges its load path.
- The English source is `en` (else `en-US`, `en_US`, `en-GB`, `en_GB`). Every non-English
  locale is compared with it key by key, by Ruby I18n's rules: `%%` is a literal `%`; `\w`
  in a name is ASCII only; `count` may be added in plural forms. A plural form the source
  lacks (`few`, `many`) is checked against the source's `other`. A missing placeholder in a
  `zero`, `one` or `two` form is a warning, not an error. These are the same rules as
  l10n-guard 0.10.0's `rails` kind, written separately in `rails_rate.py`.
- **Look-alike error:** the ASCII `%{name}` is missing and the translation has it with a
  look-alike percent sign (`％`, `٪`, `﹪`) or fullwidth braces (`｛｝`).
- **Kinds of missing placeholder:** look-alike percent, look-alike brace, spaced
  (`% {date}`, `%{ date }`), Ruby hash (`#{name}`), no percent (`{name}`, `{{name}}`), other
  syntax (`${name}`, `%(name)`, `%name%`), renamed (another `%{...}` instead), dropped.
- "Chinese, Japanese, Korean or Arabic-script locale" means the language subtag is one of
  `zh ja ko ar fa ur ps ckb sd ug`.
- The code is `rails_rate.py` 0.1.0 with 15 offline tests. It runs once, in a sealed
  container, and writes every file, locale and problem it finds to CSV.

## Predictions

- **P1** Fewer than 2% of the compared (repository, locale) pairs have at least one
  look-alike placeholder error.
- **P2** Every look-alike placeholder error is in a Chinese, Japanese, Korean or
  Arabic-script locale.
- **P3** The share of placeholder strings with a look-alike error is higher in those
  locales than in all other locales together (the one-sided Fisher p is reported, not
  required).
- **P4** Missing-placeholder errors outnumber look-alike errors at least 10 to 1.
- **P5** At least 95% of the YAML files under `config/locales/` load with PyYAML.
- **P6** At least 180 of the 214 pinned commits can still be fetched, and at least 40
  repositories have a non-English translation compared with English.
- **P7** "Dropped" is the most common kind of placeholder error.

A prediction that fails will be reported as failed, with the reason.

## Known limits, stated before the run

- The commits are from 2024 or earlier. Some of these problems will have been fixed since.
  The study measures the pinned snapshot, not today's apps.
- It reads files, not code. A key no view uses still counts, and an app that passes a
  variable the English never uses can make an "extra" placeholder harmless. A dropped
  placeholder can be a deliberate translation choice. The counts describe translation files.
- Merging every file under `config/locales/` recursively assumes the app loads them all.
  Rails' default load path reads only the top folder, and most apps that nest add the rest.
- A few large apps (Discourse, Mastodon, GitLab, Diaspora) have many locales and will
  dominate string-level totals. Results are reported per repository too.
