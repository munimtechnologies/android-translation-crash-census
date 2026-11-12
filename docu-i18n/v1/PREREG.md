# Pre-registration: Docusaurus translations that are never built (docu-i18n census v1)

Marker: docu-i18n census PREREG v1

Written 2026-11-12 by AI agents working in the name of MV2 of Munim, Inc.
(mv2@munimtech.com), before any repository in the population has been read. The code that
will run is in this folder (`docu_core.py`, `docu_census.py`, `mech.py`, `test_docu.py`); the
census waits until this file is public. Text CC BY 4.0, code Apache-2.0.

## Question

Docusaurus, the documentation site generator, builds only the locales listed in
`i18n.locales`. For each listed locale it reads translations from
`<site>/<i18n.path>/<localeConfigs[locale].path or the locale name>/`, and since 3.9 it
switches translation off without a warning when that exact folder does not exist
(`packages/docusaurus/src/server/i18n.ts`: `translate` defaults to `pathExists(localizationDir)`).
It never looks at folders it was not told about. That allows two quiet failures:

- **orphan**: a translated folder such as `i18n/de/` whose locale is not listed. It is never
  built, so its readers never see it.
- **mismatch**: a listed locale whose folder name differs only in case or `_`/`-`, such as
  `zh-CN` listed with `i18n/zh-cn/`. It works on a case-insensitive disk (macOS, Windows), but
  a Linux build (GitHub Actions, Netlify, Vercel) serves English pages under `/zh-CN/`.

We found no earlier count of either (a web search on 2026-11-12 turned up only the
Docusaurus docs and PR #11304).

## Mechanism check M (real build, `mech.py`)

One tiny site, built with `docusaurus build` 3.10.2 in a Linux container. It lists en, fr,
zh-CN, pt-BR and ja, with ja using `localeConfigs` path `japanese`. Its one page has a
translated copy in five folders.

- K (control): `/fr/` shows the French text from `i18n/fr`.
- K2 (control): `/ja/` shows the text from `i18n/japanese`.
- W1: `/zh-CN/` exists and shows the English text. The `i18n/zh-cn` text appears nowhere.
- W2: `/pt-BR/` exists and shows the English text. The `i18n/pt_BR` text appears nowhere.
- W3: the `i18n/de` text appears nowhere and there is no `/de/` folder.

If K or K2 fails, the build check is broken and W1-W3 say nothing. If W1 or W2 fails,
mismatch folders are not a bug on this version, and no issue or pull request is filed about one.

## Population

The union, de-duplicated, of:
1. every `source: 'https://github.com/<owner>/<repo>...'` in the Docusaurus showcase,
   `website/src/data/users.tsx` at commit c4a39d6c0cfd7148b818e1ddc7454cdd646817ba;
2. GitHub repository search (sorted by stars, the first 1,000 results each, unauthenticated):
   `topic:docusaurus fork:false archived:false stars:>=2`, and
   `"built using Docusaurus" in:readme fork:false archived:false` (the sentence in the
   Docusaurus template README) split into stars `>=20`, `5..19` and `2..4`.
Forks and archived repositories are dropped. Showcase repositories come first, then the rest
by stars, up to 3,000. Each repository is cloned at HEAD (depth 1). Every
`docusaurus.config.{js,ts,mjs,cjs,mts}` is a site, up to 3 per repository, skipping those under
node_modules, example(s), template(s), test(s), fixtures, e2e, vendor and create-docusaurus.

## Method

- The config is read without running it. Only a literal `i18n: {...}` object with string
  literals for `defaultLocale`, `locales`, `path` and `localeConfigs.*.path` counts as
  **parsed**. A site with no `i18n` anywhere gets Docusaurus's default (en only). Anything else
  (variables, spreads, environment lookups) is **unparsed** and left out of every share.
- Each folder directly under the site's i18n folder is **configured**, **mismatch**,
  **variant-dup** (a variant while the exact folder also exists) or **orphan**
  (`docu_core.classify`).
- **Substantive**: for each non-configured folder, up to 25 of its Markdown files (seeded
  sample) that map to an English source (`docs/`, `../docs/`, `versioned_docs/`, `blog/`,
  `src/pages/`) are compared with that source with all whitespace removed. A folder is
  substantive if at least 3 differ. Files identical to the English copy count as copies, not
  translations. (Lesson from our linguas-script census: count content before calling a
  catalog lost.)
- **Deliberate signals** for a folder: its name in quotes in a config comment (commented),
  elsewhere in the config code (mentioned), or `--locale <name>` in package.json, netlify.toml,
  vercel.json or a GitHub workflow (cli, meaning a per-locale build). Crowdin config presence is
  recorded.

## Gate and predictions (verdicts are computed by `docu_census.grade`)

- **G**: at least 500 parsed sites, and at least 40 of them with an i18n folder other than the
  default locale's. If G fails, P1-P3 are NOT TESTABLE and only counts are reported.
- **P1**: among sites with such a folder, 5% to 40% have at least one substantive orphan folder.
- **P2**: at least 1 site has a substantive mismatch folder, and at most 10% of sites with
  folders have any mismatch folder.
- **P3**: at most half of the substantive orphan folders carry a deliberate signal (not
  testable with fewer than 5).
- **H** (graded by hand afterwards): the job draws 12 substantive folders (up to 4 mismatch, the
  rest orphan, seed "docu-i18n census v1"). For each, a person-level check of the repository
  (config history, README, issues, and for a mismatch the live site's `/<locale>/` page) labels
  it **lost** (a real translation the project evidently meant to publish, or one with no sign of
  a deliberate hold-back) or **not lost** (deliberately held back, published another way,
  machine-generated filler, or superseded). H holds if at least 2/3 of the drawn folders are
  lost. Labels go into `labels.csv` with a one-line reason each.

## What happens next

- Results go into RESULTS.md in this folder, negatives first, with every verdict as computed.
  Anything decided after seeing data is labelled post hoc.
- Upstream reports only if M (K, K2, W1 or W2 as relevant) and H hold, one a day at most,
  after reading each project's contributing rules, and each says it was made with AI agents.
  Mismatch folders come first, because a one-line rename fixes them.
- A check for this pattern goes into l10n-guard only after a separate pre-registration.

## Limits stated now

- The population is what GitHub search and the showcase surface, not all Docusaurus sites.
  Search results above 1,000 per query are cut off (recorded as truncated).
- Configs built from variables are left out, and that may hide sites with i18n set up.
- Translations pulled from Crowdin at build time are not in the repository, so neither class
  sees them. For a mismatch, the H check of the live site settles it.
- "Differs from English after whitespace removal" is a weak translation test. H is the check.
