# Pre-registration: Weblate's "Linux style" language codes under glibc and Python gettext

weblate-linux-codes PREREG v1. Written 2026-11-12, before the test job runs. Made with AI agents
working for MV2 of Munim, Inc. (mv2@munimtech.com). Code: Apache-2.0. Text and data: CC BY 4.0.

## The question

Weblate names a project's translation files with a per-component "Language code style". Its
maintainer recommends the "Linux style" for gettext projects whose catalogs must load on Linux
(WeblateOrg/weblate#18159, 2026-02-23). That style comes from two tables in
`weblate/formats/base.py`. Commit e748c7be19c947d65b9936fe56be10b363e5c742 (2026-02-23, "fix:
extend list of legacy Linux locale codes") added the second one:

- `LEGACY_CODES`: `zh_Hans` -> `zh_CN`, `zh_Hant` -> `zh_TW`, `zh_Hans_SG` -> `zh_SG`,
  `zh_Hant_HK` -> `zh_HK`
- `LINUX_CODES`: `sr_Latn` -> `sr`, `sr_Cyrl` -> `sr@cyrillic`, `ar_Latn` -> `ar@latin`,
  `kk_Latn` -> `kk@latin`, `be_Latn` -> `be@latin`, `uz_Cyrl` -> `uz@cyrillic`, `uz_Latn` ->
  `uz@latin`

In glibc, the Serbian locale `sr_RS` is written in Cyrillic and `sr_RS@latin` in Latin. GNOME,
for example, names its Serbian catalogs `sr` (Cyrillic) and `sr@latin` (Latin). glibc's gettext
and Python's `gettext` module try the locale's own name and then shorter forms of it, so a
`sr_RS.UTF-8` user is served the catalog named `sr`. If that is right, the Linux style gives
Serbian Cyrillic users the Latin translation, and no Serbian locale ever loads the catalog named
`sr@cyrillic`. Uzbek looks reversed in the same way: glibc's `uz_UZ` is Latin and `uz_UZ@cyrillic`
is Cyrillic, so a catalog named `uz@latin` would never load. Weblate's language data has no
`uz_Cyrl` and maps `uz@cyrillic` to `uz`, so a project's Cyrillic Uzbek file is Weblate's `uz`.

This job tests those claims with the real tools instead of reasoning about them.

## Method (`weblate_linux.py`, run in a `python:3.12` container with GNU gettext and glibc locales)

1. Wait until this file is public in the repository.
2. Download `weblate/formats/base.py` at the commit above and on `main`, and read `LEGACY_CODES`
   and `LINUX_CODES` with Python's `ast` module (the file is never imported or run). Download
   Weblate's `language-data` `aliases.csv` and `languages.csv` (for an exploratory round-trip table
   only).
3. Generate the locales `sr_RS.UTF-8`, `sr_RS.UTF-8@latin`, `sr_ME.UTF-8`, `uz_UZ.UTF-8`,
   `uz_UZ.UTF-8@cyrillic`, `be_BY.UTF-8`, `be_BY.UTF-8@latin`, `zh_CN.UTF-8` and `zh_TW.UTF-8` with
   `localedef`, and measure each locale's own script from its name for Monday
   (`nl_langinfo(DAY_2)`), counting Cyrillic against Latin letters.
4. For four two-language projects, install one-message catalogs side by side in one locale tree,
   each answering with the Weblate code it came from: Serbian (`sr_Cyrl`, `sr_Latn`), Uzbek (`uz`
   as Cyrillic, `uz_Latn`), Belarusian (`be` as Cyrillic, `be_Latn`) and Chinese (`zh_Hans`,
   `zh_Hant`). Each project is built twice: with the names Weblate's Linux style gives (from the
   pinned tables), and with the usual Linux names (`sr`/`sr@latin`, `uz@cyrillic`/`uz`,
   `be`/`be@latin`, `zh_CN`/`zh_TW`).
5. With only `LANG` set (no `LANGUAGE`), ask which catalog each locale reaches, using glibc's
   `gettext` program and Python's `gettext.translation(..., fallback=True)`.

## Predictions (each graded separately for glibc and for Python; Python verdicts end in `py`)

- **T (gate):** the pinned tables say `sr_Latn` -> `sr`, `sr_Cyrl` -> `sr@cyrillic`, `uz_Latn` ->
  `uz@latin`, `be_Latn` -> `be@latin`, `zh_Hans` -> `zh_CN` and `zh_Hant` -> `zh_TW`.
- **S (gate):** all locales except `sr_ME.UTF-8` generate, and Monday is written in Cyrillic in
  `sr_RS.UTF-8`, `uz_UZ.UTF-8@cyrillic` and `be_BY.UTF-8`, and in Latin in `sr_RS.UTF-8@latin`,
  `uz_UZ.UTF-8` and `be_BY.UTF-8@latin`. (`sr_ME`'s script is reported, not predicted.)
- If T or S fails, or a catalog fails to build, W1-W3, K and F are NOT TESTABLE.
- **W1:** with Weblate's Linux-style names, `sr_RS.UTF-8` (a Cyrillic locale) reaches the
  `sr_Latn` catalog.
- **W2:** with Weblate's Linux-style names, the `sr_Cyrl` catalog is reached from none of
  `sr_RS.UTF-8`, `sr_RS.UTF-8@latin` and (if it generates) `sr_ME.UTF-8`.
- **W3:** with Weblate's Linux-style names, `uz_UZ.UTF-8` (a Latin locale) reaches the Cyrillic
  `uz` catalog, and the `uz_Latn` catalog is reached from neither Uzbek locale.
- **K (control):** with Weblate's Linux-style names, `be_BY.UTF-8` reaches `be`,
  `be_BY.UTF-8@latin` reaches `be_Latn`, `zh_CN.UTF-8` reaches `zh_Hans` and `zh_TW.UTF-8`
  reaches `zh_Hant`. If K fails, the harness is suspect and W1-W3 are not claimed even if they
  hold.
- **F (fix):** with the usual Linux names, every Serbian, Uzbek and Belarusian locale in S reaches
  the catalog written in its own measured script, and the Chinese locales reach `zh_Hans` and
  `zh_Hant`.

## What we already know (stated so it isn't mistaken for a result)

- The tables above were read from Weblate's `main` on 2026-11-12. The blame view attributes the
  whole `LINUX_CODES` block to e748c7b. No Weblate test or doc for these entries was found.
- Weblate's `language-data` maps `sr@cyrillic` -> `sr_Cyrl`, `sr@latin` -> `sr_Latn`,
  `uz@cyrillic` -> `uz`, `uz@latin` -> `uz_Latn` and `be@latin` -> `be_Latn`. It also has a
  separate language `sr` (Serbian). So under the Linux style a project with both `sr` and `sr_Latn`
  would get the file name `sr` twice. This follows from the tables alone and is reported, not
  tested.
- The linguas-script census (same repository, 2026-11-12) showed that glibc and Python never load
  catalogs named `zh_Hans`, `zh_Hant` or `sr_Latn` from a normal locale, and that `sr@latin` loads
  from `sr_RS.UTF-8@latin`.
- Nothing in this job reads any project's repository. No result was computed before this file was
  written.

## After the job

`RESULTS.md` reports every verdict, negatives first, with the job's `summary.json`,
`lookups.json` and `roundtrip.csv` published unchanged. If T, S, K, W1 and W2 hold for both glibc
and Python, MV2 will open one issue on WeblateOrg/weblate describing the Serbian mapping (and
Uzbek if W3 holds), linking these results, offering a pull request, and saying that the work was
made with AI agents. If `main` has changed these entries by the time the job runs, the job still
tests the pinned tables, and no issue is filed for anything already fixed.
