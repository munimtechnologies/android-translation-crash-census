# qt-args 0.1.0: what Qt translations with mismatched %N place markers show

MV2 of Munim, Inc., made with AI agents. Text CC BY 4.0, code Apache-2.0.
Written 2026-10-17, before the first run. Results will be added in RESULTS.md after
they have been read by hand.

## Question

When a translation in a Qt `.ts` file has a different set of `%1`, `%2`, ... place markers
from its English source, what does the app show? Checkers (Qt Linguist's "Place Marker
Matches" validation, `lrelease -fail-on-invalid`, Weblate's Qt format check) flag the
mismatch. They don't say which mismatches only lose a value and which put a value in
the wrong place. This census sorts every mismatch in 39 open-source Qt projects by what
`QString::arg()` actually does with it.

## The rule it simulates

From qtbase `src/corelib/text/qstring.cpp` (read at commit 7faa468):

- Each single-argument `arg()` call replaces the **lowest-numbered** marker still in the
  string (`findArgEscapes`: larger numbers are skipped, a smaller one resets the
  count). The multi-argument `arg(a, b, ...)` sorts the marker numbers and gives the i-th
  argument to the i-th smallest. Both put argument i in the i-th smallest marker of the
  **translation**.
- A marker is `%`, an optional `L`, then one or two digits. `%0` counts, `%01` is `%1`,
  and `%100` is `%10` followed by a `0`.
- Non-ASCII digits (Bengali `%১`, Arabic-Indic `%١`): since Qt 6.6 they are not markers
  unless the environment variable `QT_USE_UNICODE_DIGIT_VALUES_IN_STRING_ARG` is set
  (`supportUnicodeDigitValuesInArg`). Before 6.6 they were accepted in single-argument
  calls. The multi-argument parser at that commit reads only ASCII digits. The census uses
  the Qt 6.6 default and reports separately which rows would differ on older Qt.
- If no marker is left, `arg()` returns the text unchanged and logs
  `QString::arg: Argument missing`.

So, for a source with markers `%1 %2`:

| translation has | the app shows | category |
|---|---|---|
| `%2 ... %1` | both values, in the translator's order | ok |
| `%1` only | the first value; the second is lost | dropped |
| `%2` only | the **first** value where the second belongs | wrong_value |
| `%1 ... %3` | the second value in `%3` | wrong_value |
| `%1 ... %2 ... %50` (Turkish "%50" percentage) | both values; `%50` stays as text | ok |
| `%50` only | the first value in place of "%50" | wrong_value |

## Scope and limits

- The same 39 projects as qt-shape 0.1.0, at their default branches; copies of Qt's own
  translation files are skipped.
- Counted: non-plural messages whose English source has at least one marker. Finished
  and unfinished translations are counted apart (lrelease can ship unfinished ones
  unless `-nounfinished` is given). Plural (numerus) and obsolete messages are skipped
  and counted: in a numerus message `%n` is filled by `tr()` itself, which needs its
  own rules.
- It assumes the code passes as many arguments as the source has distinct markers.
  Usually true, but every row is a candidate to read in the project's code, not a
  confirmed bug. Rows are checked by hand before any result is published.
- This is a counting pass with no predictions. A pre-registered test, if one follows,
  will take its minimum sample sizes from these counts.

## Prior work we found

Single-project checks exist: UNetbootin PR #394 (a scripted `.ts` check across 12
languages), QGroundControl issue #15174 (Crowdin syncs bringing back dropped markers),
Nextcloud desktop issue #11027 (`% 1` in Danish). A validator in miguelaguiar01/corpus
(issue #1003) encodes the lowest-marker rule. We found no census across many projects that
sorts mismatches by what the app displays, and none that measures the Qt 6.6
non-ASCII-digit change on real translations.

## Files

- `qt_args.py`: the census (`python qt_args.py --data-dir DIR --out-dir DIR`)
- `test_qt_args.py`: its tests (`python -m unittest -v test_qt_args`)
