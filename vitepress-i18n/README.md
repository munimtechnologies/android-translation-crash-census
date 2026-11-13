# vitepress-i18n: translated folders a VitePress site serves under the wrong language

`vitepress_locales.py` is a small checker (Python standard library only, no network) for
VitePress documentation sites. It finds folders of translated pages that VitePress publishes as
pages of the site's root language, because the folder's name doesn't match a key of the
site's `locales` config.

Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.

## What VitePress does (source reading, not a build test)

This was read in [vuejs/vitepress at commit 40b2e09](https://github.com/vuejs/vitepress/tree/40b2e090772ac11eac358d25ec92ee435fc2adbd)
(version 2.0.0-alpha.21, 12 November 2026). VitePress 1.x was not read. Its
[i18n guide](https://vitepress.dev/guide/i18n) describes the same rule: each locale's pages live
in a folder named exactly like its key.

| Step | Source file | Behaviour |
|---|---|---|
| Which files become pages | `src/node/plugins/dynamicRoutesPlugin.ts` (`resolvePages`) | Every `**/*.md` under `srcDir`. Only `srcExclude` filters the list, and `locales` is never consulted. |
| Which locale a page belongs to | `src/shared/shared.ts` (`getLocaleForPath`) | The first key (other than `root`) for which `new RegExp('^/' + key + '/')` matches the page's route. The match is case-sensitive. With no match, the page belongs to `root`. |
| `<html lang>` | `src/node/build/render.ts` | `siteData.lang` from `resolveSiteDataByRoute`, so the matched locale's `lang`, or else the site's top-level `lang` (default `en-US`). This file doesn't read a page's front matter for it. |
| Search | `src/node/plugins/localSearchPlugin.ts` | Each page goes into the search index of the locale that `getLocaleForPath` returns. |

So a folder of German pages named `de/`, on a site whose `locales` has no `de` key, is still
built and published. Its pages carry the root locale's `<html lang>` (for example `en-US`),
nav, sidebar labels and search index, and the language switcher doesn't list them. A folder
named `zh-cn/` on a site whose key is `zh-CN` gets the same treatment, and the switcher's
`zh-CN` entry has no pages behind it.

Nothing here has been checked with a real VitePress build yet. Similar checks for Docusaurus,
Hugo and mkdocs-static-i18n are pre-registered and queued:
[docu-i18n](../docu-i18n/v1/PREREG.md), [hugo-i18n](../hugo-i18n/mech-v1/PREREG.md),
[mkdocs-i18n](../mkdocs-i18n/mech-v1/PREREG.md).

## What the checker reports

```
python vitepress_locales.py <site root holding .vitepress> [--locales root,fr] [--src-dir docs] [--strict]
```

It reads the locale keys and `srcDir` from `.vitepress/config.*` or `.vitepress/config/index.*`
without running any JavaScript, lists the Markdown pages, and classifies every top-level folder
that is a locale key or is named like a language tag:

| Status | Meaning | Finding? |
|---|---|---|
| `listed` | The folder name is a locale key. | no |
| `case_mismatch` | The name differs from a key only in case (`zh-cn` against `zh-CN`). Its pages are served as `root`. | yes |
| `separator_mismatch` | The name differs from a key only in `_` against `-`, and possibly case (`pt_BR` against `pt-BR`). Its pages are served as `root`. | yes |
| `unlisted` | The name looks like a language tag, isn't a key, and the folder mirrors the root tree (at least 2 of its pages, and at least half, have a same-path page outside language folders). | yes |
| `unlisted_dir_config` | Like `unlisted`, but the folder has its own `config.{js,mjs,ts,mts}`, which VitePress 2 reads as directory-level config and which may set `lang`. | no |
| `lang_like_not_mirrored` | Named like a language tag (for example `ml/` for machine learning) but doesn't mirror the root tree. | no |

`empty_locales` lists keys with no pages under `<key>/`. Every entry in `dirs` also reports
`served_as`, the locale VitePress picks for the folder's first page, ported from
`getLocaleForPath`. `--strict` exits 1 when there is any finding, so the checker can run in CI.

## Limits

- The config is read as text, not run. If `locales` is built from a variable, or has spread
  (`...x`) or computed (`[k]`) entries, `keys_complete` is false: pass `--locales` yourself.
  Only a `locales` object at the top level of the config object counts, so search-box
  translations (`themeConfig.search.options.locales`) are ignored.
- `rewrites` and `srcExclude` aren't modelled. The report warns when either is set.
- Folders starting with `.` and `node_modules` are skipped by this checker.
- "Looks like a language tag" means an ISO 639-1 code (or one of a few 3-letter codes) with an
  optional script and region. The mirror rule keeps folders such as `ml/` or `ts/` out of the
  findings, but a folder that copies root pages for another reason could still be flagged.

## Tests

`python -m unittest -v test_vitepress_locales` builds synthetic sites in a temporary folder:
comments and strings full of braces, a nested search `locales`, `.vitepress/config/index.ts`
configs, a case mismatch, a separator mismatch, an unlisted folder, a folder with its own
config, and a `ml/` folder that must not be flagged.
