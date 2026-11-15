# Results: l10n-guard 0.22.0 (gettext spellings)

Pre-registration: [PREREG.md](PREREG.md) (sha256 fc956d0e...1e14, checked by the job before it
ran). Build job `guard-0220-v1`, sealed container (python:3.12, Debian gettext and locales),
run 2026-11-15 08:03 UTC. The job's own output is published unchanged next to this file
(`summary.json`, `report.txt`, `compare.csv`, `mechanism.json`). Made with AI agents by MV2
of Munim, Inc. Text CC BY 4.0, code Apache-2.0.

## What did not happen, or is not shown (read first)

- **The new `linguas-spelling` warning fired on none of the 18 real po folders** checked
  (`linguas_spelling_hits: []`). It is tested only on synthetic projects and by the glibc and
  Python lookups below. How often real projects *list* a misspelled language such as `zh_cn`
  or `pt-BR` in `LINGUAS` is not measured.
- Only two real lower-case cases are known (Metamorphosis and Switcheroo, `po/zh_cn.po`, not
  listed). They were seen before the pre-registration, so R checks that the code does what it
  says on them; it is not evidence of how common the problem is.
- The pre-registration says "the 20 folders" in one sentence and 18 in S; the job read the 18
  folders of the 0.21.1 check plus the 2 known cases (20 in all). Nothing was dropped.
- The README still has one line saying a feature exists "since 0.21.1" (`still-0211.txt`);
  that line is correct and was left as it is.
- Claims are about Linux. On macOS and Windows file systems, which ignore case, a `zh_cn`
  folder may still be found.

## Verdicts (as the job wrote them)

| Prediction | Verdict |
|---|---|
| T: every test module passes after the change (23 modules, incl. new `test_0220.py`, 16 tests) | HELD |
| M1: glibc `gettext` with only `LANG` set reaches none of `zh_cn`, `pt-BR`, `nb_no`, and each control `zh_CN`, `pt_BR`, `nb_NO` from its own locale | HELD |
| M2: the same for Python 3.12 `gettext.translation(..., fallback=True)` | HELD |
| S: 0.21.1 and 0.22.0 give the same findings on the 18 po folders | HELD (18 of 18 read; 22 findings, none differ) |
| R: for Metamorphosis and Switcheroo, 0.21.1 says "add 'zh_cn'", 0.22.0 says "rename po/zh_cn.po to po/zh_CN.po and add 'zh_CN'" | HELD (both) |

All three locales were generated with `localedef` (exit 0), so M1 and M2 were testable. For each
of `zh_CN.UTF-8`, `pt_BR.UTF-8` and `nb_NO.UTF-8`, both glibc and Python found only the catalog
installed under the capitalised, underscore name.

## What changed in 0.22.0

- `linguas-unlisted` advice names the gettext spelling when the file name differs from it:
  `po/zh_cn.po` -> rename to `po/zh_CN.po` and list `zh_CN` (before: "add 'zh_cn'", which would
  install a catalog nobody loads). The `nb-NO` message is unchanged byte for byte.
- New warning `linguas-spelling`: a language listed in `LINGUAS` whose `.po` file name is not the
  gettext spelling (`zh_cn`, `pt-BR`). Skipped when the right spelling is also listed, for names
  that are not locales, and for script codes (`sr-Latn`, `zh_Hant`).

Decision rule: release only if T, M1, M2, S and R all hold. They did, so 0.22.0 is released as
built by the job (files unchanged).
