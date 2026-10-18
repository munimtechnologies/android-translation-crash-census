# Pre-registration: l10n-guard 0.10.0 on Rails and Symfony translation files

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0. Written and published
**before** the run it describes. The run's results will be added next to this file, and the
predictions will not be edited.

## What is being tested

[RAILS.md](RAILS.md) and [SYMFONY.md](SYMFONY.md) list placeholders written with a look-alike
percent sign (`％{count}`, `٪ {name}`, `％name％`, `٪ name٪`), found by searching for the characters
and reading each hit. l10n-guard 0.10.0 adds two kinds that should find them on their own:

- `rails`: a Rails locale file compared with `en.yml` key by key, by Ruby I18n's `%{name}` and
  `%<name>s` placeholders, with plural keys (`one`, `few`, `other`) checked per language;
- `symfony`: a Symfony `.yaml` or `.xlf`/`.xliff` file compared with the source language's file
  **by key**, with `%name%` parameters. This is the case a one-file XLIFF check can't see, because
  SonataAdminBundle's files have the key, not the English, as `<source>`;
- a small YAML reader built on the standard library, which refuses anchors, aliases and tags.

The test asks whether the checker finds exactly the known cases on every translation of five
projects, and nothing look-alike elsewhere.

## Inputs (pinned commits)

| Project | Files | Source | Commit |
|---|---|---|---|
| SonataAdminBundle (4.x) | `src/Resources/translations/SonataAdminBundle.<lang>.xliff`, 33 languages | `en` | `0b36030299107e2069ee249a68ecd8830b37bf93` |
| Akeneo PIM Community | `src/Akeneo/Pim/Enrichment/Bundle/Resources/translations/validators.<lang>.yml`, 28 | `en_US` | `cfc810e6449651b7d3be4c7db3dd09c71011012c` |
| OpenDXP (1.x) | `bundles/CoreBundle/translations/admin.<lang>.yaml`, 20 | `en` | `66f8e913af07e69e161d8ca13475537b2bf441fc` |
| GOV.UK Publishing Components | `config/locales/<lang>.yml`, 67 | `en` | `05d2fbe80380190b285adba9346e071b0d3a7b57` |
| OpenStreetMap website | `config/locales/ar.yml`, `ja.yml` | `en` | `855cda765f5683628bed8a83cdf963958dadc7b7` |

That is 150 translation files. The code that runs is l10n-guard 0.10.0, built in the same job
from the 0.9.0 release by a patch script and tested there first. It will be released as 0.10.0
only if every test passes. The evaluation script, `eval_0100.py`, runs once in a sealed container.

## Predictions

- **P1** Sonata: `lookalike-percent` errors only in `ja` and `zh_CN`, only on `flash_lock_error`,
  exactly 3 in each (`%name%`, `%link_start%`, `%link_end%`).
- **P2** Akeneo: the only `lookalike-percent` error is `zh_TW` `family_variant_no_axis`, and
  `tr_TR` `family_variant_no_axis` has a `placeholder-missing` error naming `%level%` (its
  translation writes `%Seviye%`).
- **P3** OpenDXP: `lookalike-percent` errors only in `zh_Hans`, only on
  `workflow_change_email_notification_text`, exactly 4 (`％s` four times).
- **P4** GOV.UK: `lookalike-percent` errors only in `ja`: 7 of them, on exactly six keys ending in
  `toggle_more`, `character_count.body`, `cookie_banner.confirmation_message.html`,
  `attachment.page.other`, `scoped_search_description` and `all_content_search_description`.
- **P5** OpenStreetMap: `ar` has `lookalike-percent` warnings and no `lookalike-percent` errors, on
  exactly three keys (`site.about.heading_html`, `site.copyright.native.html`,
  `…contributors_fi_credit_html`), because the ASCII placeholders are there too; `ja` has exactly
  one `lookalike-percent` issue, an error on `…no_applications_html`.
- **P6** Every `lookalike-percent` error is in a Chinese, Japanese or Arabic-script file.
- **P7** Every file present parses with the built-in readers, and every source file has at least
  50 string messages.

A prediction that fails will be reported as failed, with the reason.

## Known limits, stated before the run

- The YAML reader is a subset. A file that uses anchors or flow mappings is a parse error (P7
  would fail), not a silent skip.
- `rails` doesn't know which keys the app calls, so a look-alike in a string nobody displays still
  counts. The counts are about files, not about what users see.
- `symfony` reads `%s` with ASCII `%` as a placeholder. That matters only for apps like OpenDXP that
  run `vsprintf`; Symfony's own translator uses `strtr` only.
