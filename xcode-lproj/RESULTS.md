# Results: translated .lproj string tables the Xcode project never references (pre-registered)

Graded 2026-11-10 against [PREREG.md](PREREG.md) (marker "xcode-lproj census PREREG v1", sha256
49482cab1f473843f3b16eb003da4b27b2efaabaaa433e58fe7465991aa66856, printed by the job before it read
any repository). Job `xcode-lproj-v1`, run on 2026-11-10 17:11-17:14 UTC; its unit tests passed
before it read anything. Made with AI agents by MV2 of Munim, Inc. (mv2@munimtech.com). Text CC BY
4.0, code Apache-2.0.

## Verdict first: the hand check FAILED, so no rate of real findings is claimed

| Prediction | Pre-registered rule | Result |
|---|---|---|
| G (gate) | at least 250 read, at least 100 governed, at most 5% of projects unparsed | **PASSED** (334 read, 243 governed, 1 of 611 projects unparsed) |
| P1 | 2% to 20% of governed repositories flagged | HELD (45 of 243, 18.5%) |
| P2 | at least half of unreferenced files with known content are substantive | HELD (91 of 163) |
| P3 | repositories with a translation-platform config flagged more often | HELD (8 of 16 vs 37 of 227) |
| **H1** | at least 10 of 12 sampled findings real | **FAILED: 6 of 12 real** |

P1 counts repositories the detector flagged, not repositories with a real problem. With H1 failed,
**18.5% is not a rate of real untranslated apps** and must not be quoted as one. Half of the
sampled findings were not real.

## The hand check (labels in [labels.csv](labels.csv))

For each of the 12 repositories the job picked by a fixed hash, one unreferenced file was checked at
the recorded commit. The check covered the file's content, every `project.pbxproj` variant group for
that table (read through the GitHub API, raw files and Sourcegraph code search pinned to the
commit), folder references, synchronized folders and shell-script build phases.

**Real (6):** BitStore `ja` (57 of 57 strings translated; the project ships only `de` and `en`),
Pushpin `pt_BR` (86 of 91 translated; iOS falls back to the listed `pt`), MAPS.ME/omim `fa` (1,900
of 2,592 translated; no project mentions `fa.lproj`), Colloquy `ko` preferences pane (in the legacy
"Mac-Old" project), Say Their Names `ko` (about half translated), and Nio `ta` (about 88 of 89
translated). Several of these repositories are archived or inactive.

**Not real (6).** In every case the file sits outside the project as the detector said, but it holds
no translation, so nothing is lost:

- AdGuard `bg` Onboarding.strings is an empty file (0 bytes);
- AppSlate `ko` InfoPlist.strings holds only Xcode's template comment;
- Learn-iOS-Swift-by-Examples `Japanese` InfoPlist.strings holds Xcode's unfilled copyright
  template (placeholders in guillemets);
- habitica `cmn` InfoPlist.strings (a test bundle) holds only `$(PRODUCT_NAME)`;
- mhabit `zh` dev-InfoPlist.strings holds one value identical to English;
- AudioKit Synth One `zh-Hant-TW` Localizable.strings is an English copy: every value equals its
  English key.

None of the 12 labels was a close call, so no single label decided the verdict.

## Why it failed

The detector's structural rule (a language file on disk that no variant group lists) was right in
12 of 12 cases. The failure is in the content step, and in a P1 rule that counted any unreferenced
file whatever its content:

- 2 of the 6 false findings were never read, because the job reads at most 10 unreferenced files
  per repository (AdGuard, habitica);
- 2 were read but had nothing usable to compare with, so their content stayed "unknown"
  (`English.lproj` was not in the reference list; AudioKit's English file gave no matching keys);
- 2 were read and judged "not substantive" (mhabit, AppSlate), and were still counted.

**Post-hoc, not pre-registered:** all 5 sampled findings the job had labelled "substantive" were
real, and the sixth real one (Nio `ta`) had no reference file to compare with. In the full output,
25 of the 243 governed repositories (10.3%) have at least one unreferenced file that the job read
and judged substantive. That figure is an exploratory number found after the labels. It is a
hypothesis for the next test, not a result.

## What changes next

[xcode-lproj-v2](../xcode-lproj-v2/PREREG.md) pre-registers a corrected rule and tests it on a new
population, the open-source macOS apps list (serhii-londar/open-source-mac-os-apps), leaving out
every repository used here. Under the new rule a file counts only if it holds at least one value
that differs from its key and from English, and is not empty, a build variable or an Xcode template.
The new job reads every candidate file (up to 50 per repository) and also compares with
`English.lproj`.

## Other observations (exploratory)

- 414 unreferenced files in the 45 flagged repositories; `InfoPlist.strings` (101) and
  `Localizable.strings` (136) dominate. 152 of the 347 listed files are in a language the project
  declares in `knownRegions`, so Xcode knows the language even though the file is missing.
- 25 repositories were left out as generated (XcodeGen or Tuist files). The rule also matched model
  files that happen to be named `Project.swift` (for example in FSNotes and Kickstarter), which
  wrongly left those repositories out. v2 counts `Project.swift` only alongside other Tuist files.
- 1 of 611 project files did not parse.

## Files

- [summary.json](summary.json), [sample.csv](sample.csv) and [unreferenced.csv](unreferenced.csv)
  are byte-identical job outputs. The per-repository table can be regenerated by re-running
  [xcode_lproj_census.py](xcode_lproj_census.py), because every repository is read at a fixed commit.
- [labels.csv](labels.csv): the hand labels with the evidence for each.

Limits: one curated list of mostly well-known iOS apps; precision only, never recall; a file the
project lists but no target copies is not counted.

Made with AI agents by MV2 of Munim, Inc. (mv2@munimtech.com).
