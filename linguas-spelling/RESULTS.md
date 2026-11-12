# Results: LINGUAS names that gettext never looks up (zh_cn, pt-BR, en-us)

linguas-spelling census v1, graded 2026-11-12 against [PREREG.md](PREREG.md) (sha256
`95e372f024d11b62289cbf858fdf72c3731409d9390b3a6f1984a21665b9b805` as recorded by the job;
published before the job ran, commit 3f94c4a). The job ran 2026-11-12 15:14-15:19 UTC.
Made with AI agents working for MV2 of Munim, Inc. (mv2@munimtech.com). Code: Apache-2.0.
Text and data: CC BY 4.0.

## Negatives first

- **H (hand check) FAILED: 3 of 4 flagged repositories confirmed; all 4 were needed (90%).**
  The one that failed is `yeKcim/warmux`. Its two flagged directories
  (`old/wormux-0.7.9/po` and `old/wormux-0.8beta1/po`) sit inside archived copies of old source
  trees. The repository has no build files at its top level, and Flathub's `org.gna.Warmux`
  builds the warmux 11.04.1 release tarball, so the build that ships never reads these LINGUAS
  files. The census code treats every LINGUAS directory with a build file next to it as
  "governed", and can't tell an archived tree from the one that is built.
- Because H failed, the pre-registered next step ("the cases back l10n-guard 0.22.0's
  `linguas-spelling` warning and become one-line fix pull requests, one a day") does **not**
  follow from this census. Any report to a project is checked by hand on its own first.
- The problem is rare, as predicted, and its effect on users is small. Two of the three real
  cases also ship a plain `pt` catalog. A `pt_BR` user of those apps falls back to European
  Portuguese, not to English. The third case changes one word for US English users.
- The mechanism (that glibc and Python gettext never load these spellings from a normal locale)
  is not tested by this census. It is prediction M1/M2 of the l10n-guard 0.22.0
  pre-registration, which has not run yet. If M1 or M2 fails, the claim that these catalogs are
  never loaded is withdrawn, as PREREG.md says.

## What held

| Verdict | Prediction | Result |
|---|---|---|
| G PASSED | at least 480 repositories read, at least 450 still governed | 526 of 526 read without error; 526 governed |
| P1 HELD | flagged share of governed repositories between 0.5% and 5% | 4 of 526 = 0.76% |
| P2 HELD | at least half of the flagged names are `zh` or `pt` | 4 of 5 flagged names are Portuguese (`pt-BR` twice, `pt-br`, `pt_br`); the fifth is `en-us`. No Chinese name was flagged |
| P3 HELD | no repository translated on l10n.gnome.org is flagged (at least 20 needed) | 0 of 111 |

Control: GNOME Calculator's `po/LINGUAS` passed (at least 30 languages, none flagged). All 11
unit tests passed before the census ran.

## Post-hoc (not pre-registered; read with care)

- Leaving out warmux's archived trees, 3 of 526 governed repositories (0.57%) ship a translation
  under a misspelled name. That is still inside P1's range.
  - `Diegovsky/riff`: `pt-br`.
  - `elly-code/jorts`: `pt_br`.
  - `childishgiant/mixer`: `en-us`. Its catalog has 11 messages; one differs from the source,
    `Centre` to `Center`.
- No flagged name was shadowed (the right spelling also listed), and no flagged name had a
  `.po` file under the right spelling next to it.
- The same 526 repositories list 68 script-coded names (`zh_Hans`, `zh_Hant`, `sr_Latn`,
  `be_Latn`), the subject of the separate [linguas-script](../linguas-script/RESULTS.md) census.
  Script-coded names are about 14 times as common as misspelled ones in this population.
- The census classes `pt_br`, `pt-BR` and `pt-br` alike. Every real case is a Brazilian
  Portuguese catalog named the way a web or Android project would spell it.

## Limits

- One snapshot of one population: Flathub apps whose repositories the linguas census v1 code
  could read and whose build reads LINGUAS (Meson or autotools).
- Whether the build that ships reads a given LINGUAS was checked only for the 4 sampled
  repositories, which were all of the flagged ones. A future version should skip directories
  under archived or vendored trees (`old/`, `third_party/`, `subprojects/`) or check the
  Flathub manifest.
- The hand check read each project's `po/` folder, `po/meson.build` and main entry file, not
  the whole code. An app or desktop that sets `LANGUAGE` itself could still load these catalogs.

## What happens next

- l10n-guard 0.22.0's `linguas-spelling` warning is graded on its own pre-registered tests
  (M1, M2 and the others in `l10n-guard-0220/PREREG.md`), not on this census.
- No issues or pull requests will be filed on the strength of this census. If M1 holds, the
  `riff` case may be reported to its project after a fresh hand check of its current code and
  contribution rules, with AI disclosed.

## Files

[v1/](v1/) holds the job's outputs unchanged (`summary.json`, `entries.csv`, `repos.csv`,
`sample.csv`, `results.jsonl`) and the hand-check labels (`labels.csv`). The code that produced
them is [linguas_spelling.py](linguas_spelling.py), with tests in
[test_linguas_spelling.py](test_linguas_spelling.py).
