# sphinx-i18n: translations a Sphinx build never compiles or never finds

`sphinx_locales.py` is an offline checker that uses only the Python standard library. It reads a Sphinx project's `conf.py` as text, without running it, and its `locale_dirs` folders. It then reports translation catalogs that a build for a given language never compiles or never looks up, so the "translated" site comes out in English with no error.

Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.

## What Sphinx does (source reading, not a build test)

This comes from reading [Sphinx v9.2.0](https://github.com/sphinx-doc/sphinx/tree/v9.2.0) and CPython's `Lib/gettext.py` and `Lib/locale.py` (3.12). No real Sphinx build has tested it yet.

| Step | Where | Behaviour |
|---|---|---|
| Which catalog folders are compiled | `sphinx/util/i18n.py`, `CatalogRepository.locale_dirs` | Only `<srcdir>/<locale_dir>/<language>/LC_MESSAGES`, with `language` used exactly as given. There is no lowercasing and no `-` to `_`. Otherwise Sphinx logs a verbose-only "does not exist" message. |
| When `.po` becomes `.mo` | `sphinx/builders/__init__.py`, `compile_catalogs` | Only for the folders above, and only if `gettext_auto_build` is true (the default). |
| How translations are looked up | `sphinx/transforms/i18n.py` then `sphinx/locale.init` | `gettext.translation(domain, localedir=d, languages=[language])` for every `locale_dirs` entry `d`. |
| What gettext tries | CPython `gettext.find` and `_expand_lang` | `locale.normalize`, then every combination, most specific first. `pt_BR` gives `pt_BR.ISO8859-1, pt_BR, pt.ISO8859-1, pt`. Note that `de` gives `de_DE.ISO8859-1, de_DE, de.ISO8859-1, de`. |

So **lookup falls back to related folders but compilation does not**. With `-D language=pt_BR` and only a `pt/` folder of `.po` files, gettext would accept `pt/`'s `.mo` files, but Sphinx never builds them, and the output is English. Folder names that differ from the language only in case (`zh_cn` against `zh_CN`) are missed by both steps on case-sensitive filesystems (Linux, Read the Docs) and work on default macOS or Windows. Folder names that differ in separator (`pt-br` against `pt_BR`) are missed everywhere.

The `pt-br` case was reported as [sphinx-doc/sphinx#11749](https://github.com/sphinx-doc/sphinx/issues/11749) (closed as not planned). The `locale` against `locales` default was settled in [#13025](https://github.com/sphinx-doc/sphinx/issues/13025) (the default is `['locales']`). We found no report of the compile-versus-lookup fallback gap.

**Read the Docs.** Its project language codes are lowercase with a dash (`pt-br`, `zh-tw`), and so is `READTHEDOCS_LANGUAGE`. Its default Sphinx build maps six of them back (`nb-no, pt-br, es-mx, uk-ua, zh-cn, zh-tw` become `nb_NO, pt_BR, es_MX, uk_UA, zh_CN, zh_TW`) and passes `-D language=...` (`readthedocs/doc_builder/backends/sphinx.py`, `get_language`). A `conf.py` that sets `language` from `READTHEDOCS_LANGUAGE` is overridden by that flag. With custom `build.commands`, or when the variable reaches Sphinx some other way, the dashed code matches no `pt_BR/` folder.

## Usage

```
python sphinx_locales.py <srcdir holding conf.py> [--language pt_BR] [--rtd-language zh-tw]
                         [--locale-dirs locales,../locale] [--strict]
```

Pass the values your build really uses. `--language` is what reaches `-D language=`. `--rtd-language` is a Read the Docs project language, which is mapped as above. Without either, the checker uses a literal non-English `language` from `conf.py`, if there is one. The output is JSON. `--strict` exits 1 on any finding, so the checker can run in CI.

| Finding | Meaning |
|---|---|
| `fallback_uncompiled` | No exact folder. A folder gettext would fall back to has `.po` files but no `.mo`, and Sphinx never compiles it. |
| `case_mismatch` / `separator_mismatch` | A catalog folder differs from a looked-up name only in case or in `-` against `_`. |
| `missing` | No folder that Sphinx or gettext looks up for a non-English language (for example `zh_Hant/` for Read the Docs `zh-tw`, which becomes `zh_TW`). |
| `auto_build_off` | `gettext_auto_build = False` and the exact folder has `.po` files without `.mo`. |
| `no_lc_messages` | `.po` files sit in a language folder but not under `LC_MESSAGES`. |
| `locale_dirs_default_mismatch` | `conf.py` does not set `locale_dirs`, there is no `locales/`, and catalogs sit in `locale/`. |

Warnings (not findings): `fallback_mo` (the language is served only from a fallback folder's committed `.mo` files, which Sphinx never rebuilds), `duplicate_*_mismatch` (an exact folder exists alongside a near-miss one), `language_from_rtd_env`, `locale_dirs_not_literal`, `locale_dir_missing`, `no_language`.

## Limits

- Source reading only, at Sphinx v9.2.0. Older Sphinx versions were not read.
- `conf.py` is parsed with `ast` and never executed. The last top-level or nested assignment wins. Values built at run time are reported as expressions, so pass `--locale-dirs` or `--language` for those.
- Domains are compared as catalog file paths. Which domain each document uses (`gettext_compact`) is not modelled. A fallback folder only counts when the exact folder yields no compiled catalog at all.
- Lookup uses the running Python's own `gettext._expand_lang`, so alias tables can differ slightly between Python versions.
- Sphinx's own UI strings (the `sphinx` domain) take a different path (`repo.locale_dirs`, exact folders only), and this checker does not cover them separately.

## Tests

```
python -m unittest -v test_sphinx_locales
```

The tests build synthetic projects in a temporary folder. They cover an exact folder, a `pt` fallback with and without committed `.mo` files, `zh_cn` against `zh_CN`, `pt-br` against `pt_BR` in both directions, a duplicate near-miss, the Read the Docs `zh-tw` mapping, `locale/` without `locale_dirs`, `gettext_auto_build = False`, `.po` files outside `LC_MESSAGES`, a `READTHEDOCS_LANGUAGE` `conf.py`, and the `--strict` exit codes.
