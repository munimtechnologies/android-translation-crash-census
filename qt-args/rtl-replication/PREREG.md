# Pre-registration: do right-to-left Qt translations write `%1` as `1%` in other projects too?

MV2 of Munim, Inc., made with AI agents, 2026-10-17. Text CC BY 4.0; code Apache-2.0.

This file, [rtl_replicate.py](rtl_replicate.py) and its tests are committed **before** the job
that reads the new projects' translation files runs. No `.ts` file of any project below was
opened while writing them. The only things looked at were that `veyon/veyon` has a
`translations/` folder and that `rizinorg/cutter-translations` and `psi-im/psi-l10n` exist
(file and folder names, no translation text).

## What is being tested

[RTL.md](../RTL.md) reported, as an **exploratory** finding from the qt-args census of 39 Qt
projects, that finished right-to-left translations (Arabic, Persian, Hebrew, Urdu, Uyghur,
Yiddish, Pashto) write a place marker digit-first, `1%` instead of `%1`, in 294 of 7,911 cases
(3.7%), against 147 of 172,310 (0.085%) in all other languages. Without Scribus's Arabic file
the right-to-left count was still 127 (1.6%, a lower bound), from at least 14 projects. The
pattern was noticed in that data and counted in the same data, so it needs a test on data
nobody has looked at.

## The new corpus (fixed now)

The 40 GitHub repositories listed in `REPOS` in [rtl_replicate.py](rtl_replicate.py): open-source
Qt applications believed to keep Qt Linguist `.ts` files in the repository, read at their
default branch when the job runs. They were chosen from general knowledge of Qt projects, for
having translations at all, not for anything about their right-to-left files.

- None is one of the 39 exploratory projects, a repository of one of their owners (so no other
  LXQt, Deepin, Nextcloud or Sigil-Ebook repository), or a known fork or ancestor of one
  (ownCloud client, the original GoldenDict, KeePassX, TokTok qTox, qBittorrent Enhanced). The
  script refuses to run if this check fails.
- A repository that fails to clone, has no `.ts` files, or has no right-to-left files stays in
  the list and is reported as such. None will be replaced or added after the job runs.

## Measures (the same as RTL.md)

Everything reuses qt_args.py 0.1.0 unchanged ([METHOD.md](../METHOD.md)); the job records the
SHA-256 of the copy it ran.

- **Unit:** a finished (not unfinished, plural, obsolete or vanished) translation in a `.ts`
  file whose language is not English and whose source language is English, of a source text
  with at least one Qt place marker. Copies of Qt's own translations are skipped.
- **Reversed:** the translation's markers lose or misplace a value (qt_args `dropped` or
  `wrong_value`) and the **first** hint qt_args gives is `reversed`: the missing marker's digit
  followed by `%`, with no digit before it, where the source has no such text.
- **Groups:** right-to-left = `ar fa he ur ug yi ps`; excluded from both groups = `ku ckb sd dv
  syr ks prs azb mzn glk lrc bal arc bqi sdh pnb` (often written in Arabic script or right to
  left, not counted in RTL.md); other = every remaining language.
- **Test:** one-sided Fisher exact test that the right-to-left reversed rate is higher.

## Predictions and how they are graded

- **Enough data:** at least 500 right-to-left and 10,000 other finished translations with
  markers. If not, the verdict is **too little data** and nothing is claimed either way.
- **P1:** the right-to-left reversed rate is at least **5 times** the other languages' rate,
  with one-sided **p < 0.001**.
- **P2:** right-to-left reversed rows come from at least **3** repositories.
- **P3:** with the repository that has the most right-to-left reversed rows left out entirely
  (both groups), the rate is still at least **5 times** higher, with **p < 0.01**.

Verdict: **replicated** if P1, P2 and P3 hold; **partly replicated** if P1 holds but P2 or P3
fails; **not replicated** if there is enough data and P1 fails.

Reported but not graded: the same comparison counting a `reversed` hint anywhere in the row,
rates per language, per repository and per file, and the excluded group's counts.

## Checks by hand after the job

Before anything is written up, at least 20 right-to-left reversed rows (all, if fewer) and at
least 10 other reversed rows are read with their text. Each is called a real digit-first
marker or something else (for example a percentage in the text). If more than 20% of the
right-to-left rows read are not digit-first markers, the result is reported with that
correction next to the graded verdict, which stays as computed.

## Deviations

If a bug in the code is found after the job runs, the fix and both sets of numbers are
published, with the first run's verdict kept and the reason stated. Any other change to this
plan after the job starts will be listed here with its date.

## Limits known in advance

- `.ts` files whose language is in neither the file's `language` attribute nor an
  `_xx` part of its name are not counted (as in the census).
- Projects that share a translation platform team with an exploratory project (for example
  through Transifex or Weblate) are not fully independent of it; the per-repository table will
  show how much of the result rests on any one project.
- A replication shows the pattern is common, not why it happens. RTL.md's caution stands: we
  make no claim about who or what wrote these strings.
