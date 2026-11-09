# Deviations: ios-lproj census

Made with AI agents by MV2 of Munim, Inc. Text CC BY 4.0.

## 2026-11-09: job ios-lproj-v1 stopped before reading any repository; re-run as ios-lproj-v2

- **What happened.** ios-lproj-v1 ran on 2026-11-09 from 10:50 to 10:54 UTC and stopped at its first run
  step, `python -B -m unittest -v test_lproj_census`. Python could not import the test module:
  `test_unknown` wrote a bytes literal containing a non-ASCII letter
  (`b'... "Zrušit";'`), which is a `SyntaxError` ("bytes can only contain ASCII literal
  characters"). No test ran, and the census step never started. No repository and no list was
  read, so nothing was seen before this change.
- **The change.** That one line now builds the same bytes with `'... "Zrušit";'.encode("utf-8")`.
  The test's input and expected result (`holds_translation == "unknown"`) are unchanged. No other
  line of the test file changed except a dated comment at the top.
- **Not changed.** `lproj_census.py` (the census code), PREREG.md, every prediction (G, P1-P4, H1),
  the population, the sample rule and the outputs. The v2 job downloads `lproj_census.py` from this
  folder on GitHub and prints its sha256 next to the test file's, so the code that runs is the code
  that was published before any data was read.
