# census_callsites 0.1.0 results: the rules find every missed crash, but they are not selective

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-17 from the sealed run of 2026-10-17
(05:13-05:28 UTC). Licence: this text CC BY 4.0.

**One of three pre-registered predictions held (C1). C2 and C3 failed.** The predictions were
[published first](PREDICTIONS.md). Output: [callsites.json](callsites.json) (counts, the audit
comparison, the predictions) and [findings.csv](findings.csv) (every flagged translation, with the new
`callsite` column). The hand check of the new candidates is in
[candidates-audit.csv](candidates-audit.csv).

## The run

The census re-read the F-Droid index for this run, so the repositories and commits differ slightly
from census 0.4.0's run of 2026-10-16. This time 4,476 repositories were attempted and 1,271,320
translations formatted. 360 throw whatever the app passes, in 94 repositories. By code use: 230
formatted, 41 candidate, 1 referenced, 88 never named. We did not trace which 2 rows that census 0.4.0
called formatted are gone from this read. The 2 new candidate rows below were not in census 0.4.0's
findings at all.

## Predictions

| Prediction | Result | Numbers |
|---|---|---|
| C1. At least 80% of the hand-audited rows that throw are "formatted" or "candidate" | HELD | 34 of 34 |
| C2. The 2 audited rows that are not formatted stay "referenced" | FAILED | Commons nqo stayed referenced; Your local weather ar `title_activity_license` became a candidate (rule `stored`) |
| C3. At most half of the strings census 0.4.0 calls "referenced" become candidates | FAILED | 40 of 42 |

C1 is mostly a fit check: we wrote the rules from those 40 rows. It does show that the rules, as
coded, match the code we had described in prose. All 40 audited rows were still crashing translations
on this read.

C3 failed, and it was a weak test. Census 0.4.0 looks up code use only for strings with a flagged
translation. So the pool of "referenced" strings was not the large out-of-sample set we assumed. It
was 42 strings, and 36 of them are the audit's own. Of the 6 outside the audit, 5 became candidates.
The rules cannot be called selective. The `stored` rule is the loose one: it needs only a reference
outside a call, plus any call anywhere in the repository that formats a string id given by a
variable.

On the audited rows, "candidate" covers 39 rows: 25 uncaught crashes, 8 caught throws, 1 throw whose
trigger is not confirmed, and 5 that don't crash (NewPipe in, the census's own false positive; HeartBeat
bn `[zero]`, an item Android never picks; 2 ownCloud ug strings that are never reached; and Your local
weather ar, not formatted). So 34 of 39 throw, and 25 of 39 crash the app.

## Out of sample: two new reachable crashes, confirmed by reading the code

Of the 41 candidate crash rows, 39 are audited rows. The other 2 are new, both in
[Automation](https://git.server47.de/jens/Automation) (com.jens.automation2, F-Droid), string
`httpParametersExplanation`, rule `wrapped`:

- German: "... Wenn der Parameter mit 2 % endet, ..." The source's `%2$s` became "2 %", so "% e"
  reads as a float conversion (`% e`) and gets a String: IllegalFormatConversionException.
- Dutch: "... Als de parameter eindigt op %2 s, ..." `%2 s` has no conversion letter:
  UnknownFormatConversionException.

`ActivityManageActionTriggerUrl.onCreate` runs
`tvHttpParameterExplanation.setText(String.format(getResources().getString(R.string.httpParametersExplanation), Miscellaneous.httpMainData, Miscellaneous.doNoEncodingString))`.
Both arguments are `String` constants ("httpMainData", "NoEncoding"), and the call is not inside a
try/catch. So opening the screen that configures a "trigger URL" action should crash the app in German
and Dutch. We read this at commit 64936ce in source and did not run it on a device. A search of the
project's issue tracker for "crash" (2026-10-17) returned nothing.

Census 0.4.0 missed it because the lookup sits behind `getResources().` inside `String.format(...)`,
the receiver-chain pattern the audit found in Helsinki Timetables. This is the one place the new rules
found something new. It is a real pair of crashes, but only 2 rows.

## What changes

- The reachable count on this read is at least 257: 230 formatted + the audit's 25 crashes + these
  2. (That it equals census 0.4.0's floor of 257 is a coincidence; the reads differ.) The census README
  still gives census 0.4.0's figures.
- "candidate" stays a label for "read this call site", as designed. It is not a reachability verdict,
  and the census's headline numbers will not count candidates without reading them.
- For the next census version: compute code use for every string id, not only those with a flagged
  translation, so a rule's selectivity can be measured on a real out-of-sample pool. Tighten `stored`
  so the dynamic format call has to sit in the same file or class as the stored id.

## Limits

- The rules read text, not types. The audit rows they were written from are in-sample.
- The Automation crash is read in source, not reproduced. It has not been reported to the project
  yet.
