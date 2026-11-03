# Deviations from the zh-vocab pre-registration

zh-vocab DEVIATION 1. Written 2026-11-03 by AI agents working for MV2 of Munim, Inc., before
the second run reads any repository. Nothing in [PREREG.md](PREREG.md) changes.

## 1. The first run crashed while writing flagged.csv; the second run uses a CSV-safe wrapper

**What happened.** The first full run (job `zh-vocab-v1`, 2 November 2026, about 13:07 UTC)
read about 4,500 of the 4,693 repositories and then stopped with
`UnicodeEncodeError: 'utf-8' codec can't encode characters ...: surrogates not allowed` in
`csv.DictWriter.writerow`. It wrote no `summary.json` and no `sample.csv`, so no verdict was
computed. Its partial `flagged.csv` and `repos.jsonl` will not be used or published.

**Why.** `zh_vocab.py` 0.1.0 decodes Android's `\uXXXX` escapes one UTF-16 unit at a time. An
emoji written in a strings file as two escapes (a surrogate pair) becomes two lone surrogate
characters in the decoded text, and Python refuses to write those as UTF-8.

**What changes.** The second run (job `zh-vocab-v2`) runs the published `zh_vocab.py` 0.1.0
byte for byte (downloaded from `main`; its SHA-256 is recorded in `summary.json` under
`runner`) through [run_zh_vocab.py](run_zh_vocab.py), which replaces only the CSV writer that
`zh_vocab.py` uses. Before a row is written to `flagged.csv` or `sample.csv`, each text value has
its surrogate pairs joined into the character they encode, and any half left over replaced with
U+FFFD. [test_run_zh_vocab.py](test_run_zh_vocab.py) reproduces the crash with the plain writer
and checks that the wrapper writes the same row.

**Why the results can't be affected.** Lone surrogates are not Han characters (so they never
make or unmake a unit), never match a key of OpenCC's phrase table (so they never make or unmake
a flag), and are not part of the fields hashed to draw the sample. The counts, verdicts V1-V3
and the V4 sample are computed exactly as pre-registered. Only how some emoji appear in the CSV
text columns differs.

**Other differences.** The second run reads the repositories on a later day (3 November or after),
so HEAD commits can differ from the first run's. Each repository's commit is recorded as before.
