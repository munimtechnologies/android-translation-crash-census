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

So **lookup falls back to related folders but compilation does not**. With `-D language=pt_BR` and only a `pt/` folder of `.po` files, gettext would accept `pt/`'s `.mo` files, but Sphinx's own auto-build never builds them, and the output is English. Folder names that differ from the language only in case are missed by compilation on case-sensitive filesystems (Linux, Read the Docs) and work on default macOS or Windows; lookup misses them in one direction only (see the correction below). Folder names that differ in separator (`pt-br` against `pt_BR`) are missed everywhere.

The `pt-br` case was reported as [sphinx-doc/sphinx#11749](https://github.com/sphinx-doc/sphinx/issues/11749) (closed as not planned). The `locale` against `locales` default was settled in [#13025](https://github.com/sphinx-doc/sphinx/issues/13025) (the default is `['locales']`). We found no report of the compile-versus-lookup fallback gap.

**Read the Docs.** Its project language codes are lowercase with a dash (`pt-br`, `zh-tw`), and so is `READTHEDOCS_LANGUAGE`. Its default Sphinx build maps six of them back (`nb-no, pt-br, es-mx, uk-ua, zh-cn, zh-tw` become `nb_NO, pt_BR, es_MX, uk_UA, zh_CN, zh_TW`) and passes `-D language=...` (`readthedocs/doc_builder/backends/sphinx.py`, `get_language`). A `conf.py` that sets `language` from `READTHEDOCS_LANGUAGE` is overridden by that flag. With custom `build.commands`, or when the variable reaches Sphinx some other way, the dashed code matches no `pt_BR/` folder.

## Correction and prior-art check, 16 November 2026

- **Source re-checked.** On Sphinx's `master` branch (16 November 2026), `CatalogRepository.locale_dirs` still builds `basedir / locale_dir / language / 'LC_MESSAGES'` with no normalisation and logs a missing folder at verbose level only, and `sphinx.locale.init` still passes `[language]` unchanged to `gettext.translation`. Sphinx 9.2.0 is still the latest release on PyPI. The table above stands. Read the Docs' mapping (`OLD_LANGUAGES_CODE_MAPPING` in `readthedocs/projects/constants.py`, built from `nb_NO, pt_BR, es_MX, uk_UA, zh_CN, zh_TW`) also still matches.
- **Tracker.** Six searches of Sphinx's issue tracker (fallback and `locale_dirs`; `pt_BR` translation; `gettext_auto_build` and `.mo`; `LC_MESSAGES` and language folder; "not compiled"; case-sensitive locale) found no earlier report of the compile-versus-lookup gap. The nearest are #11749 (above); [#6591](https://github.com/sphinx-doc/sphinx/issues/6591), a Spanish build that compiled 0 `.po` files, closed in 2019 with no confirmed cause; and [#9634](https://github.com/sphinx-doc/sphinx/issues/9634) (next point).
- **Older Sphinx.** Before Sphinx 7.4.0 (15 July 2024; [PR #9635](https://github.com/sphinx-doc/sphinx/pull/9635), fixing #9634), `sphinx.locale.init` also passed the bare language as a second lookup language (`[language, language.split('_')[0]]`). gettext normalises a bare `zh` to `zh_CN`, so a `zh_TW` build could pick up Simplified Chinese strings from a `zh_CN/` folder. On Sphinx older than 7.4.0, lookup can therefore reach more folders than this checker models. The bare-language fallback this page describes (`pt_BR` to a literal `pt/` folder) comes from gettext itself and is still there after that fix.
- **What the docs say.** The configuration page says `locale_dirs` "are searched by the gettext module" (which implies gettext's fallback) and that with `gettext_auto_build` "Sphinx builds a .mo file for each translation catalog file". In the source only catalogs under `<locale_dir>/<language>/LC_MESSAGES` are built. The internationalisation guide shows the `locale/<lang>/LC_MESSAGES` layout by example only and does not say how `<lang>` must be spelled. We read the gap as designed behaviour that the docs describe more broadly than the code, not as a bug.
- **New limit: `sphinx-intl build`.** Run without `-l`, `sphinx-intl build` compiles every folder in the locale directory whose name starts with a lowercase letter, `pt/` included. A project that runs it before `sphinx-build`, or that commits `.mo` files (reported as the `fallback_mo` warning), does get the gettext fallback. `fallback_uncompiled` is therefore only right for builds that rely on Sphinx's own auto-build, for example a default Read the Docs build. The checker cannot see build scripts.
- **Correction (case).** The first version of this page said case-only differences are "missed by both steps". That holds when `language` is `zh_CN` and the folder is `zh_cn/`. In the other direction (`language = 'zh_cn'`, folder `zh_CN/`), `locale.normalize` maps the code to `zh_CN.gb2312`, so gettext does find committed `.mo` files in `zh_CN/`, and only compilation misses the folder. The checker already uses gettext's own expansion and reports that case as `fallback_mo` or `fallback_uncompiled`, so its findings are unchanged; only that sentence overstated it.
- **Upstream.** Sphinx's [AI policy](https://www.sphinx-doc.org/en/master/internals/ai-policy.html) asks that a human check and submit every pull request and that AI not write issue or pull request text. This page is therefore not being sent upstream as an issue or pull request by the agents that wrote it.

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

- Source reading only, at Sphinx v9.2.0 (re-checked on `master`, 16 November 2026). Before 7.4.0, Sphinx also looked up the bare language (see above).
- Build scripts are not read: a `sphinx-intl build` step (or any other `msgfmt` run) before `sphinx-build` compiles fallback folders, which turns `fallback_uncompiled` into a working fallback.
- `conf.py` is parsed with `ast` and never executed. The last top-level or nested assignment wins. Values built at run time are reported as expressions, so pass `--locale-dirs` or `--language` for those.
- Domains are compared as catalog file paths. Which domain each document uses (`gettext_compact`) is not modelled. A fallback folder only counts when the exact folder yields no compiled catalog at all.
- Lookup uses the running Python's own `gettext._expand_lang`, so alias tables can differ slightly between Python versions.
- Sphinx's own UI strings (the `sphinx` domain) take a different path (`repo.locale_dirs`, exact folders only), and this checker does not cover them separately.

## Tests

```
python -m unittest -v test_sphinx_locales
```

The tests build synthetic projects in a temporary folder. They cover an exact folder, a `pt` fallback with and without committed `.mo` files, `zh_cn` against `zh_CN`, `pt-br` against `pt_BR` in both directions, a duplicate near-miss, the Read the Docs `zh-tw` mapping, `locale/` without `locale_dirs`, `gettext_auto_build = False`, `.po` files outside `LC_MESSAGES`, a `READTHEDOCS_LANGUAGE` `conf.py`, and the `--strict` exit codes.
