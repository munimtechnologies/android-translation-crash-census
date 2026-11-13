# astro-i18n: locale folders that Astro's own i18n helpers disagree on

`astro_locales.py` is a small checker for Astro sites that use Astro's built-in i18n routing
(the `i18n` block in `astro.config.*`, not Starlight). It uses only the Python standard library
and needs no network. It finds locale folders in `src/pages` where `Astro.currentLocale` and
`getRelativeLocaleUrl()` don't agree. In those folders, either the pages carry the default
language, or Astro's own language links point to a folder that isn't there.

Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.

## What Astro does (source reading, not a build test)

This was read in [withastro/astro at commit 5b7c327](https://github.com/withastro/astro/tree/5b7c3275cf2f4aa0d1685495f943cb19039a2e83)
(astro 7.4.12, 13 November 2026).

| Helper | Source | Behaviour |
|---|---|---|
| `Astro.currentLocale` | `packages/astro/src/i18n/utils.ts`, `computeCurrentLocale` | For each URL segment, a string locale is skipped unless `segment.includes(locale)`, which is sensitive to case and to `_` versus `-`. Only after that check does it compare the normalized forms. An object locale matches if `path === segment`, or if one of its `codes` equals the segment after normalizing. If no segment matches, the result is the default locale. |
| Normalizing | `packages/astro/src/i18n/path.ts`, `normalizeTheLocale` | `_` becomes `-`, then everything is lowercased. |
| `getRelativeLocaleUrl`, `getAbsoluteLocaleUrl` and the URL lists | `packages/astro/src/i18n/index.ts`, `getLocaleRelativeUrl` | `normalizeLocale = true` by default, so the URL segment is the normalized string locale, or the normalized `path` of an object locale. Astro's [docs](https://docs.astro.build/en/reference/modules/astro-i18n/) show `getRelativeLocaleUrl("fr_CA", ...)` returning `/fr-ca/...`. |
| Config validation | `packages/astro/src/core/config/schemas/refined-validators.ts` | Nothing checks the case or separators of locales. |

The [routing guide](https://docs.astro.build/en/guides/internationalization/) says folder names
must match the `locales` items exactly, and suggests lowercase and hyphens "for greatest
compatibility". That suggestion matters more than it sounds. For a string locale that isn't
already lowercase with hyphens, such as `'pt-BR'` or `'fr_CA'`, **no folder name satisfies both
helpers**:

- A folder named exactly like the locale (`src/pages/pt-BR/`) gets the right
  `Astro.currentLocale`. But `getRelativeLocaleUrl('pt-BR')` links to `/pt-br/`. That differs
  only in case, so whether it reaches the folder depends on the server; most Linux-based static
  hosts match paths case-sensitively. For `fr_CA`, links go to `/fr-ca/`, which never reaches
  `fr_CA/` on any server.
- A folder named like the links (`src/pages/pt-br/`) is reached by the links. But
  `"pt-br".includes("pt-BR")` is false, so `Astro.currentLocale` is the default locale on every
  page in it, and so is anything built on it, such as `<html lang>` or which strings get loaded.

The object form satisfies both: `{ path: 'pt-br', codes: ['pt-BR'] }`, with the folder named
`pt-br`. Then `Astro.currentLocale` is `pt-BR` and the links go to `/pt-br/`. If the entry is the
`defaultLocale`, set `defaultLocale` to the new `path` as well (Astro checks it against paths).

Prior reports: [withastro/astro#17984](https://github.com/withastro/astro/pull/17984) proposed
making `Astro.currentLocale` ignore case and separators. A maintainer closed it as working as
expected. We found no report about the combination with `getRelativeLocaleUrl`'s default
normalizing, and no checker. Nothing here has been checked with a real Astro build yet.

## What the checker reports

```
python astro_locales.py <site root> [--locales en,pt-BR,spanish=es|es-MX] [--default en] [--pages-dir src/pages] [--strict]
```

It reads `i18n.locales`, `defaultLocale` and `routing.prefixDefaultLocale` from
`astro.config.*` as text, without running any JavaScript. Then it lists the pages under
`src/pages` and checks each locale entry against Python ports of the Astro functions above.

For each locale entry it reports `link_segment` (the segment Astro's links use) and
`spelling_ok` (whether any folder name works with both helpers). When `spelling_ok` is false it
adds `suggested_entry` (the object form). It also reports every top-level folder that is the
locale or normalizes to it:

| Folder status | Meaning | Finding? |
|---|---|---|
| `ok` | `Astro.currentLocale` is this locale and the links reach the folder. | no |
| `current_locale_wrong` | `Astro.currentLocale` on these pages is another locale, usually the default. | yes |
| `links_miss` | `Astro.currentLocale` is right, but the links use a different spelling (`fr-ca` for `fr_CA/`). | yes |
| `links_case_only` | As above, but the spellings differ only in case. Whether the links work depends on the server. | yes |

Also reported:

- `unlisted_dirs`: top-level folders named like a language tag that aren't a configured locale.
  Status `unlisted` (a finding) means the folder mirrors the root pages (at least 2 of its
  pages, and at least half, have a page at the same path outside the language folders), so its
  pages get the default `Astro.currentLocale`. `lang_like_not_mirrored` (for example `ml/` for
  machine learning) is not a finding.
- `later_segment_pages`: default-language pages where a later URL segment equals a locale, such
  as a post at `/blog/de`. `Astro.currentLocale` checks every segment, so the result is `de`.
  This is intended (see [withastro/astro#9970](https://github.com/withastro/astro/issues/9970)),
  so it's listed for review, not counted as a finding.

`--strict` exits 1 when there is any finding, so the checker can run in CI.

## Limits

- The config is read as text, not run. If `locales` is built from a variable or has spread
  entries, `locales_complete` is false, and you should pass `--locales` (objects as
  `path=code|code`).
- Only top-level folders under `src/pages` are checked. Top-level dynamic folders such as
  `[lang]/` produce a warning: their paths come from `getStaticPaths` and aren't checked.
- If the site passes `normalizeLocale: false` anywhere under `src/`, the report warns. Links
  from those calls keep the configured spelling, but the link check assumes the default.
- Fallback rewrites, `domains` and custom middleware aren't modelled.

## Tests

`python -m unittest -v test_astro_locales` checks the ported functions against the examples in
Astro's PR and docs. It also builds synthetic sites in a temporary folder, covering: a comment
and a string holding a fake `i18n` block, spread and template-literal entries, `i18n` from a
variable, a case mismatch, a separator mismatch, an object locale with an uppercase `path`, an
unlisted folder, a `ml/` folder that must not be flagged, a later-segment page, a dynamic
`[lang]/` folder and a `normalizeLocale: false` call.
