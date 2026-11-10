# Results: l10n-guard 0.20.1 (0.20.0 plus Android Lint's donottranslate rule)

Graded 2026-11-10 against [PREREG.md](PREREG.md) (sha256 `5a22cb25…7aea`, public before the new code
ran). Job: `guard-0201-v1`, run once, 2026-11-10 05:17-05:20 UTC; its outputs are in [v1/](v1/)
unchanged. The hand check was done by AI agents working in the name of MV2 of Munim, Inc., reading
the repositories, not by the projects' maintainers. Code Apache-2.0, text CC BY 4.0.

## Outcome: released as l10n-guard 0.20.1

The release rule was: T, R1-R6 and H2 all hold. They all held.

| | Prediction | Result | Verdict |
|---|---|---|---|
| T | Every test module passes after the change (strict) | 21 of 21 modules pass (test_packaging now included; 0 failing) | HELD |
| R1 | The 4 census rows found not real come out clean | 4 of 4 | HELD |
| R2 | At least 11 of the 12 confirmed rows still flagged | 12 of 12 | HELD |
| R3 | None of the 17 orphans that `localeFilters` drop is reported | 0 reported | HELD |
| R4 | At most 2 of the 28 real 0.19.0 findings lost | 0 lost (28 of 28 read) | HELD |
| R5 | Server Box `az` phantom and AliasVault `fa` orphan not reported | both absent | HELD |
| R6 | Clock `th`, Clock `ca`, mighty-alarm-clock `ja` reported again | all 3 | HELD |
| H2 | At least 14 of 16 fresh repositories have a real finding | **16 of 16** | HELD |
| H3 | At least 4 in 5 checked findings real | **33 of 33** | HELD |

Gate for H2/H3: 80 held-out repositories read (needed 60), 16 drawn (needed 8). No label was
borderline, so no verdict depends on a judgement call.

## What changed and what it fixed

0.20.0 failed only R4: three real orphans fell just under the 50% line because each app's
`values/donottranslate.xml` was counted in the module's strings. 0.20.1 leaves files whose name
starts with `donottranslate` out of every count, as Android Lint's `TranslationDetector` does.
With that, R6 held and R4 lost nothing. We said in the pre-registration that these three known
cases shaped the change; the fresh sample below is the test that they did not shape.

The same build fixes the 0.19.0 packaging test (the README has two versioned `pip install`
lines; the test now checks that every one names this version), so T held strictly this time.

## Fresh sample (H2, H3): the hand check

16 held-out repositories drawn by `sha256("l10n-guard 0.20.1 fresh v1|" + repo)`, the 16 checked
for 0.20.0 moved to the end (none were needed), up to 3 findings each: 33 findings, 16 orphans
and 17 phantoms. For each finding we read, at the recorded commit, the locale list, the folder
(exists? empty? which language?) and the module's Gradle file for language filters.
Labels: [labels.csv](labels.csv).

- **Orphans (16 of 16 real).** Each left-out folder holds the language it is named for: Bitmask
  `it`/`et`/`ro`, Retro Music `or`/`ca`, Ltt.rs `zh`/`cs`/`ja`, WallpaperExport `hi`/`th`,
  Imagepipe `es`, Barcode Scanner `th`/`et`, Homer Player 2 `uk`/`ru`, Haven `sr`. None of these
  modules sets a language filter. Homer Player 2's list names 3 languages while the app ships more,
  and its Gradle file says in a comment that the app should support all languages.
- **Phantoms (17 of 17 real), three kinds:**
  - empty `strings.xml` (`<resources></resources>` or a few bytes): OsmAnd `fur`/`rup`/`gn`,
    MediLog `fa`, RedReader `mr`, Barcode Scanner `ia`, ownCloud `br`, Futon `gu` (its only string
    is the name `Keiyoushi`);
  - a Crowdin export holding comments and no strings: Amaze `bs`/`fy`/`br` (one 1,826-byte file);
  - no folder at all: Phonograph Plus `bg`/`hr`, ownCloud `dv`/`prs`, Pachli `tzm`;
  - an untranslated English copy: Retro Music `da` (a 34 KB `values-da-rDK/strings.xml` in English),
    which is exactly the case 0.20.0 was built to catch.

## Negatives and limits (read these)

- **This is a precision test, not a recall test.** It shows the reported findings are real; it
  does not measure what 0.20.1 misses. On the held-out set it reports 138 orphans and 387 phantoms,
  against 151 and 401 for 0.19.0 ([v1/summary.json](v1/summary.json)); the findings behind that
  net drop (13 orphans, 14 phantoms) were not hand-checked here.
- **The sample is not fully independent.** Bitmask appears twice in the held-out set (the 0xacab.org
  upstream and the CalyxOS GitLab fork, both flagged for `et`, `it` and `ro`); the CalyxOS copy was
  drawn.
- **Post-hoc observation, not graded:** Pachli lists `tzm-Tfng`, and its `values-ber` folder holds
  27 strings in Tifinagh. Android picks resources by language code, so those strings are not shown
  for the listed `tzm`; the finding is real, but the useful fix may be a folder rename rather than
  dropping the language. Imagepipe's list uses folder spellings (`nb-rNO`, `pt-rBR`), which the
  `locale-config-tag` code covers; none of those findings was in the sample.
- **Same reviewers, same rule.** The labels follow the 0.19.0 rule and were made by AI agents.
  Phantoms of the empty-file kind are easy to judge; orphans were judged from a few quoted strings
  per folder, not a full read.

## Exploratory (held-out set, 80 repositories at HEAD)

| | 0.19.0 | 0.20.1 |
|---|---|---|
| Repositories flagged | 66 | 63 |
| Orphan findings | 151 | 138 |
| Phantom findings | 401 | 387 |

Phantom checks were skipped for 2 Flutter apps and 1 list whose default language is not English
and was not identified. The totals equal 0.20.0's (equal totals do not prove that no single
finding moved).

## Files

- Published before the run: [PREREG.md](PREREG.md), [guard_job_0201.py](guard_job_0201.py),
  [block_0201.txt](block_0201.txt), [test_0201.py](test_0201.py) (plus 0.20.0's
  [guard_job.py](../l10n-guard-0200/guard_job.py) and
  [holdout_0200.py](../l10n-guard-0200/holdout_0200.py), downloaded unchanged).
- [labels.csv](labels.csv): hand labels for the fresh sample.
- [v1/](v1/): job outputs, unchanged. In them, columns named `0200` hold the 0.20.1 results.
  `pkg/` is the released build: [l10n-guard v0.20.1](https://github.com/munimtechnologies/l10n-guard/releases/tag/v0.20.1).
