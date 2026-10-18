# qt-count results: look-alike counts in Qt plural messages stay in a few projects

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0; code Apache-2.0.
Plan: [PREREG.md](PREREG.md), committed before the job ran. Code: [qt_count.py](qt_count.py).
Data: [data/](data/). Nothing was run in the apps.

## Verdict: **both predictions failed**

[qt-numerus](../qt-numerus/FINDINGS.md) found Qt translations whose plural messages write the
count `%n` with the Arabic percent sign (`٪n`) or the fullwidth one (`％n`), so users see the sign
and the letter instead of the number. Those cases were found by searching for the characters.
This census asked how common they are, in the 40 Qt projects of the
[right-to-left replication](../qt-args/rtl-replication/RESULTS.md), whose plural messages nobody
had read. The job read all 40 at their default branches on 2026-10-18 (06:45-06:51 UTC) with
l10n-guard 0.7.0 (sha256 `d18b120e60ce9c2f…`, recorded by the job).

| fresh corpus (40 projects) | finished plural messages with `%n` | look-alike count |
|---|---:|---:|
| Arabic-script and CJK languages | 1,094 | 0 |
| all other languages | 4,284 | 0 |

- **P1** (finished look-alike counts in at least 2 of the 40 projects): **failed**, 0 projects.
- **P2** (higher look-alike rate in Arabic-script/CJK languages, one-sided Fisher p < 0.01, with at
  least 200 and 2,000 messages): **failed**. There was enough data (1,094 and 4,284), but there
  were no look-alikes on either side (p = 1).

By the rule fixed in advance: the problem is limited to a few projects. 20 of the 40 projects have
finished plural messages with `%n`; x64dbg has no `.ts` files.

How small "none" is: with 0 of 1,015 CJK messages (Chinese 599, Japanese 295, Korean 121), a rate
above about 0.3% would probably have shown at least one case (rule of three, 95%). The fresh
Arabic-script side is small, only 79 messages (Arabic 60, Persian 9, Urdu 9, Uyghur 1, from eight
projects), so it rules out only rates above about 4%.

## Where the look-alikes are (39 qt-args projects, not graded)

The 39 qt-args projects were counted too but not graded, because some of their files had already
been read by hand. They have 9,346 finished plural messages with `%n`, and 41 with a look-alike
count. All 41 are in four projects:

| project | look-alike plural messages | languages |
|---|---:|---|
| Bitcoin Core | 19 | Arabic 11 (of 12 finished), Chinese 8 (the same string in 8 Chinese-script files) |
| QOwnNotes | 10 | Japanese 6, Urdu 2, Chinese 2 |
| KeePassXC | 8 | Arabic 8 (of 16 finished) |
| Nextcloud desktop client | 4 | Arabic 4 |

The self-check worked: the four files already read by hand (Bitcoin Core Arabic, KeePassXC Arabic,
QOwnNotes Urdu and Japanese) all show look-alikes. Nextcloud's Arabic file is the one case not
named in the plan. Its four strings also write the place markers `%1` and `%2` as `٪ 1` and `٪ 2`,
so the file names are lost along with the count.

Across all 79 projects, 48 have finished plural messages with `%n`, and look-alike counts turn up
in only those four. Compare the same languages in the two corpora:

| | fresh (40) | qt-args (39) |
|---|---:|---:|
| Arabic-script look-alike / finished | 0 / 79 | 25 / 206 |
| CJK look-alike / finished | 0 / 1,015 | 13 / 1,238 |

This comparison was not pre-registered and the qt-args side includes files that were searched for
these characters, so it says only that the cases cluster, not why.

## Hand check

As the plan required, rows were read with their text ([data/rows.csv](data/rows.csv)):

- **Fresh look-alike rows:** there are none.
- **All 41 qt-args look-alike rows.** In every one, `٪` or `％` stands where the count belongs, either
  right before `n` or with a space (`٪ n`). Examples: Bitcoin Core's Arabic `٪n يوم` for
  `%n day(s)` and `(مطلوب ٪n غيغابايت للسلسلة الكاملة)` for `(%n GB needed for full chain)`;
  its Chinese `（完整區塊鏈需要％n GB）`; KeePassXC's Arabic `تنتهي صلاحيته في <b>٪n</b> ثانية`
  for `Expires in <b>%n</b> second(s)`; QOwnNotes's Japanese `…さらに％n個のメモ` for
  `…and %n more note(s)`. None is a percentage in the text, so there are no false positives.

## Other things the data shows (not graded)

- **`% n` with a space** (shown as written): 2 fresh messages (MediaElch Norwegian, Mixxx French)
  and 22 in qt-args, mostly QOwnNotes (13) and KeePassXC (6, of which 5 Catalan).
- **`%1` instead of `%n`** where the source has no `%1`: 14 fresh messages (Qt Creator 5,
  QElectroTech 3, fooyin 2 and four others) and 42 in qt-args (MuseScore 14, Subsurface 10).
  `tr()` fills only `%n`, so `%1` stays on screen unless the code also calls `arg()`, which it has no
  reason to do when the source has no `%1`. The call sites were not read.
- **No `%n` in any form:** 17 fresh and 73 qt-args messages (Tiled 28, QOwnNotes 22). This is
  reported only as a count, because some languages leave the number out on purpose.
- **Unfinished messages** (not shown to users by default): 657 fresh and 4,418 qt-args, with 1 and
  2 of them not ok.
- **A labelling gap in the plan:** the Arabic-script/CJK list names `zh` but not `cmn`, `hak` or
  `yue`, so three Bitcoin Core Chinese-script files counted as "other". This affects only the
  ungraded qt-args table (its 3 "other" look-alikes are those files); the fresh corpus has none of
  these codes.

## What this does and does not show

Unlike the right-to-left digit-first marker (`1%` for `%1`), which
[replicated](../qt-args/rtl-replication/RESULTS.md) across 7 of 40 new projects, look-alike counts in
Qt plural messages did not show up in any new project. In this sample they are a problem of a few
projects and files, not a general feature of Arabic-script or CJK translations. A fix is still
worth making where they occur (in Bitcoin Core's Arabic file, 11 of 12 finished plural messages
lose their number), and a check finds them cheaply.

Limits: one format (Qt `.ts`) and plural messages only; the 79 projects were picked for having Qt
translations, not at random; the fresh Arabic-script sample is small; copies of a file count more
than once; nothing was run in the apps. We make no claim about who or what wrote these strings.

## How to catch it

MV2's [l10n-guard](https://github.com/munimtechnologies/l10n-guard) 0.7.1 reports a look-alike percent
sign as its own error, `lookalike-percent`, in every format it reads, including Qt plural forms.

## Files

- [data/rows.csv](data/rows.csv): every plural message that is not ok, with repository, commit,
  file, language, state, kind, context, source and all forms.
- [data/files.csv](data/files.csv), [data/repos.csv](data/repos.csv): counts per file and per
  repository (commit read).
- [data/qt_count.json](data/qt_count.json), [data/qt_count.md](data/qt_count.md): the job's own
  report, unedited.
