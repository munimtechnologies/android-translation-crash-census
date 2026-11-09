# Results: l10n-guard 0.20.0 (fixing the two gaps found in the 0.19.0 check)

Graded 2026-11-09 against [PREREG.md](PREREG.md) (sha256
`270a36d6186354924992cebd597d57d25f908d967b30f4ae640ea7d06db0dc48`, public before the new code ran on
any repository). Made with AI agents by MV2 of Munim, Inc. The hand check was done by AI agents
reading the repositories, not by the projects' maintainers. Code Apache-2.0, text CC BY 4.0.

## Outcome: not released

The release rule needed T, R1-R5 and H2 to hold. **R4 failed**, so 0.20.0 is **not released**.
0.19.0 stays the current release of [l10n-guard](https://github.com/munimtechnologies/l10n-guard).

| | Prediction | Result | Verdict |
|---|---|---|---|
| T | all existing test modules pass after the change, test_0200 passes | test_0200 passes (11 tests); 18 of 19 existing modules pass; `test_packaging` fails, but it fails the same way **before** the change (see below) | **not met as written**; no regression |
| R1 | the 4 census rows found not real come out clean | 4 of 4 | HELD |
| R2 | >= 11 of the 12 confirmed census rows still flagged | 12 of 12 | HELD |
| R3 | none of the 17 orphans that `localeFilters` drop is reported | 0 reported | HELD |
| R4 | of the 28 real findings from the 0.19.0 hand check, at most 2 are lost | **3 lost** (Clock `th`, Clock `ca`, mighty-alarm-clock `ja`) | **FAILED** |
| R5 | Server Box `az` phantom and AliasVault `fa` orphan gone | both gone | HELD |
| H2 | >= 14 of 16 fresh flagged repositories have a real finding | **16 of 16** | HELD |
| H3 | >= 4 in 5 checked findings real | **33 of 33** | HELD |

**About T.** `test_packaging.test_pip_line_names_this_version` expects the README to name the
version in exactly one `pip install "git+...@vX"` line. The README on `main` (0.19.0) has two such
lines, so this test already fails on the released code, before any 0.20.0 change (see
`build-summary.json`, `baseline`). Read strictly, T fails, which would make every other prediction
NOT TESTABLE. The job's code applied T as "no test that passed before fails after", and that held.
We report both readings. The outcome is the same either way: no release. The README/test mismatch
on `main` is a defect in the 0.19.0 release, and the next build will fix it.

## What R4's miss means

0.20.0 changed what counts as a translated string. A string left equal to a default *sentence* no
longer counts, so folders of untranslated English copies stop looking like translations (the gap
AliasVault exposed). An orphan is reported when a folder has at least half of the module's strings
translated. Three real orphans fell below that line under the new count. A spot reading of Clock's
`values-th` and `values-ca` shows near-complete translations, and they are not English copies, so the
new count, the 50% line or both are too strict for this app. We have not yet found which: the
published outputs record only which findings disappeared, not the counts behind them. A small
diagnostic job (`guard-0200-diag-v1`, exploratory, not part of this grading) is queued to print both
counts for these folders and list the strings the new rule drops. The fix will be pre-registered
again before any release.

The two gaps 0.20.0 set out to close are closed (R5). On a fresh sample it was fully precise (H2, H3).
It still cannot be released, because it loses real findings that 0.19.0 caught.

## Fresh sample (H2, H3)

16 held-out repositories drawn by `sha256("l10n-guard 0.20 fresh v1|" + repo)`, up to 3 findings
each (33 findings). For each one we read the language list at the checked commit, the Gradle
language filter where the finding names one, and the folder (its presence, emptiness or language).
All 33 are real ([labels.csv](labels.csv)); no label was borderline. Notes:

- Three launchers (Slauncher, scratchpad-launcher, CLauncher) carry the same 8-tag list
  (`en in it es-ES es-US fr-FR pt-BR ru-RU`), apparently inherited from a shared upstream.
  Their newer translations are all left out of it.
- Phantoms of three kinds were confirmed: a listed language the build's filter drops (OpenCalc `ti`,
  NotallyX `sl`), an empty `strings.xml` (KeliBoard `dv`, shosetsu `fr`/`ko`/`hi`), and no folder at
  all (zazentimer `lg`/`yo`/`si`, AndroidEasterEggs `fa`/`sq`, Athena `ca`).
- For AndroidEasterEggs we opened only the two main `res/` folders. The tool's claim covers
  every module.
- NotallyX's list also uses Android folder-style tags (`pt-rBR`, `zh-rCN`) in `locales.xml`. That is
  outside what this check reports, and we note it for a later version.

## Exploratory (held-out set, 80 repositories at HEAD)

From [v1/summary.json](v1/summary.json): 0.19.0 flagged 66 repositories, 0.20.0 flagged 63. Orphan
findings went from 151 to 138, phantom findings from 401 to 387. Phantom checks were skipped for 2
Flutter apps and for 1 list whose default language was neither English nor identified. No list had
a listed language found only in another catalog format. Without a hand check, it is not known how
many of the 13 dropped orphans are real (as with R4) and how many are English copies (as intended).

## Files

- [PREREG.md](PREREG.md), [guard_job.py](guard_job.py), [block_0200.txt](block_0200.txt),
  [holdout_0200.py](holdout_0200.py), [test_0200.py](test_0200.py) (published before the run)
- [labels.csv](labels.csv): hand labels for the fresh sample
- [v1/](v1/): job outputs, unchanged: `summary.json`, `regression.csv`, `sample0190.csv`,
  `heldout-diff.csv`, `findings.csv`, `sample.csv`, `results.jsonl`, `build-summary.json`,
  `report.txt`, `patch.diff`, `still-0190.txt`, and `pkg/` (the unreleased 0.20.0 build)
