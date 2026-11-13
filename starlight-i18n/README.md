# starlight-i18n: translations an Astro Starlight site serves under the wrong language

`starlight_locales.py` is a small checker (Python standard library only, no network) for
documentation sites built with [Starlight](https://starlight.astro.build/), Astro's docs theme.
It finds translated pages that Starlight publishes as pages of the default language,
right-to-left languages that are laid out left to right, and UI-string files Starlight never
reads. Starlight accepts all of these without an error or a warning.

Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.

## What Starlight does (source reading, not a build test)

This was read in [withastro/starlight at commit ad19424](https://github.com/withastro/starlight/tree/ad19424b2bb2b3290a13064cec28bf653d7730dd)
(`@astrojs/starlight` 0.42.11, 6 November 2026) and in Astro's `main` branch on 13 November
2026. Starlight is MIT-licensed.

| Step | Source file | Behaviour |
|---|---|---|
| A page's id | Starlight `src/loaders.ts`; Astro `src/content/loaders/glob.ts` (`generateIdDefault`) and `src/content/utils.ts` (`getContentEntryIdAndSlug`) | `docsLoader()` passes no `generateId` unless the site gives one. Astro then uses the frontmatter `slug`, or the file path with every segment run through github-slugger, which lowercases it. `src/content/docs/pt-BR/guide.md` becomes `pt-br/guide`. |
| A page's locale | `src/integrations/shared/slugToLocale.ts` | The first segment of the id, if `Object.hasOwn(locales, segment)`. Otherwise the root locale when there is one, else `defaultLocale`. The match is exact and case-sensitive. |
| Checking locale keys | `src/utils/user-config.ts` | Keys are never checked. Only `lang` is checked, and its region is upper-cased (`pt-br` to `pt-BR`). |
| Missing translations | `src/utils/routing/index.ts` | For every locale, each default-language page without a same-id page in that locale is copied in as a fallback with an "untranslated" notice. |
| Text direction | `src/schemas/locale.ts`, `src/utils/slugs.ts` | `dir` defaults to `'ltr'` and is never derived from `lang`. |
| UI strings | `src/utils/translations.ts`, `src/utils/createTranslationSystem.ts` | Files in `src/content/i18n/` are keyed by file name, with case kept, and looked up by each locale's exact `lang`. Starlight's built-in strings fall back from `pt-BR` to `pt`, but a site's own files don't. |

Put together:

- **A locale key with capital letters never matches.** With `'pt-BR': { ... }` and content in
  `src/content/docs/pt-BR/`, the pages' ids start with `pt-br`, which is not a key. The
  Portuguese pages are served as default-language pages, with the default `lang`, `dir`, UI
  strings and sidebar, and `/pt-BR/` holds only untranslated fallback copies of every page.
  [Starlight #3099](https://github.com/withastro/starlight/issues/3099) is one user's report of
  this for `zh-CN`, and [#2487](https://github.com/withastro/starlight/issues/2487) explains the
  lowercasing. A capitalised *folder* with a lowercase key (`pt-BR/` with `'pt-br'`) works.
- **A language folder that isn't a key is served as the default language.** For example `de/`
  on a site whose `locales` lists only `root` and `fr`.
- **An Arabic, Hebrew, Persian or Urdu locale without `dir: 'rtl'` is laid out left to right.**
- **A UI-string file named `pt-br.json`, `pt_BR.json` or `pt.json` is never read** for a locale
  whose `lang` is `pt-BR`. Nor is any file when the content config defines no `i18n` collection.

Nothing here has been checked with a real Starlight build yet. MV2 published the same kind of
checker for [VitePress](../vitepress-i18n/README.md) and [Sphinx](../sphinx-i18n/README.md).

## What the checker reports

```
python starlight_locales.py <site root holding astro.config.*> [--locales root=en,fr,ar=ar=rtl]
       [--default-locale en] [--docs-dir src/content/docs] [--strict]
```

It reads `locales` and `defaultLocale` from inside the `starlight({...})` call in
`astro.config.*` without running any JavaScript. It follows `locales` to a `const` in the same
file when it is passed as a variable, and reads the content config only for `generateId` and an
`i18n` collection. It then lists the docs pages as Astro would id them (`_`-prefixed files and
dot folders skipped, frontmatter `slug` honoured).

Top-level docs folders (`dirs`):

| Status | Meaning | Finding? |
|---|---|---|
| `listed` | The folder's id segment is a locale key. | no |
| `key_case` | The key differs from the folder's lowercased id segment only in case (`pt-BR`). Its pages are served as `served_as`. | yes |
| `key_case_custom_ids` | The same, but the content config sets `generateId`, so ids are not modelled. | no |
| `separator_mismatch` | The folder differs from a key in `_` against `-` (`pt_BR/` against `pt-br`). | yes |
| `unlisted` | Named like a language tag, not a key, and it mirrors the default-language tree (at least 2 of its pages, and at least half, have a same-path default page). | yes |
| `lang_like_not_mirrored` | Named like a language tag (say `ml/` for machine learning) but doesn't mirror the default tree. | no |

Also:

- `rtl_without_dir`: locales whose `lang` (or key) is written right to left, by script subtag
  or else by language (ar, ckb, dv, fa, he, ks, ps, sd, ug, ur, yi and others), whose `dir`
  is not `'rtl'`. Each one is a finding.
- `ui_files`: each file in `src/content/i18n/` is classed `used`, `case_mismatch`,
  `separator_mismatch`, `base_only` (`pt.json` when the locale's lang is `pt-BR`) or `unused`
  (no configured language). The middle three are findings.
- `empty_locales`: keys with no pages, so every page in them is a fallback copy.
- `served_as`: the locale Starlight picks for the folder's first page, ported from
  `slugToLocale`.

`findings_by_kind` counts each kind of finding. `--strict` exits 1 when there is any finding,
so the checker can run in CI, and the exit code is 2 when the root has no `astro.config.*`.

## Limits

- The config is read as text, not run. Spread (`...x`) or computed (`[k]`) entries make
  `keys_complete` false; a `locales` imported from another file can't be read. Pass
  `--locales` in those cases. Only string literals are read for `lang` and `dir`. A locale
  whose `lang` or `dir` is an expression is skipped by the right-to-left check.
- The docs folder is assumed to be `src/content/docs` (pass `--docs-dir` for another Astro
  `srcDir`). Ids use a close Python port of github-slugger, not the library itself.
- "Named like a language tag" means an ISO 639-1 code (or one of a few 3-letter codes) with an
  optional script and region. A folder that copies default pages for another reason could still
  be flagged as `unlisted`.
- Whether `/pt-BR/` and `/pt-br/` collide on a case-insensitive file system was not checked.

## Tests

`python -m unittest -v test_starlight_locales` builds synthetic sites in a temporary folder:
`locales` in a `const` with a spread and with braces inside comments and strings; a scoped
`defaultLocale`; an uppercase key, with and without a custom `generateId`; a separator
mismatch; an unlisted folder served as root and, on a site with no root locale, as
`defaultLocale`; a single-language site; Arabic and Persian locales without `dir`; and every
UI-file status.
