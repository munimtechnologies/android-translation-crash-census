# Pre-registration: how often do Qt plural messages lose their count?

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0; code Apache-2.0.

This file, [qt_count.py](qt_count.py) and its tests are committed **before** the job that
counts runs. The job reads the same 79 repositories as [qt-args](../qt-args/RESULTS.md) (39) and
its [right-to-left replication](../qt-args/rtl-replication/RESULTS.md) (40).

## What is already known, and what was not looked at

Qt fills the count of a plural ("numerus") message only where the translation has an ASCII
`%n` or `%Ln`. [qt-numerus/FINDINGS.md](../qt-numerus/FINDINGS.md) and
[MORE-PROJECTS.md](../qt-numerus/MORE-PROJECTS.md) found translations that write it with the
Arabic percent sign (`٪n`) or the fullwidth one (`％n`), so users see the sign and the letter
instead of the number: Bitcoin Core (Arabic, Chinese), KeePassXC (Arabic), QOwnNotes (Urdu,
Japanese), Otter Browser (Japanese) and OpenOrienteering Mapper (Chinese). Those were found by
searching for the characters, so nothing is known yet about how common this is.

- **The 40 replication projects ("fresh"):** their `.ts` files were read by a job on
  2026-10-17, but it counted only non-plural messages, and only those rows were read by hand.
  No plural message of these projects has been looked at. The predictions below are about them
  only.
- **The 39 qt-args projects:** some of their files (Bitcoin Core, KeePassXC, QOwnNotes) were
  read by hand for qt-numerus. They are counted and reported but **not graded**; the four
  known files are a self-check that the census finds what was seen by hand.

## Measures

- **Unit:** a finished plural message (not unfinished, obsolete or vanished) in a `.ts` file
  whose language is not English and whose source language is English, with `%n` or `%Ln` in
  its source. Copies of Qt's own translations are skipped. Language and file rules are those
  of qt_args.py 0.1.0.
- **Kinds,** read with l10n-guard 0.7.0 (downloaded from its `v0.7.0` tag; the job records
  its SHA-256), first match wins: **lookalike** (a form writes the count with `٪`, `％` or
  `﹪`), **spaced** (`% n`), **marker** (`%1` where the source has no place marker),
  **missing** (no form has `%n`), **ok**.
- **Groups:** Arabic-script and CJK languages, whose usual keyboards type `٪` or `％`
  (`ar fa ur ug ps ckb sd ks prs azb pnb zh ja ko`), and all other languages.

## Predictions (fresh corpus)

- **P1:** finished **lookalike** messages are found in at least **2** of the 40 fresh
  repositories. (If not, the problem is limited to a few projects, and the write-up says so.)
- **P2:** the lookalike rate is higher in the Arabic-script/CJK group than in other
  languages, one-sided Fisher exact test **p < 0.01**. Graded only with at least **200**
  Arabic-script/CJK and **2,000** other finished plural messages; otherwise "not graded".

Reported but not graded: spaced, marker and missing counts, unfinished messages, rates by
language and repository, and the 39 qt-args projects.

## Checks by hand after the job

Every fresh lookalike row is read with its text before anything is written up, and at least
20 qt-args lookalike rows (all, if fewer). A row whose look-alike sign is not where the count
belongs (for example a percentage in the text) is reported as a false positive next to the
graded result, which stays as computed. "Missing" is a warning, not a bug: some languages
leave the number out of a sentence on purpose. It is reported only as a count.

## Deviations

If a bug is found after the job runs, the fix and both sets of numbers are published, with
the first verdict kept and the reason stated. Any other change after the job starts is
listed here with its date.

## Limits known in advance

- A count can only be lost in a message the app shows with a number; the census reads
  translation files, not the apps, and nothing is run on a device.
- The 79 projects were picked for having Qt translations, not at random.
- We make no claim about who or what wrote these strings.
