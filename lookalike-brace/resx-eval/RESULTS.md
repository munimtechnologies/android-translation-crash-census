# Results: l10n-guard 0.8.0 on ONLYOFFICE's audit-trail translations

Graded 2026-10-18 against the predictions in [RESX-PREREG.md](../RESX-PREREG.md), which was
published (commit 0c69fee, 10:19 UTC) before the job ran (11:23-11:25 UTC). Made by MV2 of
Munim, Inc. with AI agents. Text CC BY 4.0; code Apache-2.0.

## What ran

Compute job `l10n-guard-080-v1` built l10n-guard 0.8.0 from 0.7.2, ran every test file
(55 + 6 + 14 + 21 + 13 + 7 + 14 tests, all passing, one skipped), and then checked all 26
translations of `module/ASC.AuditTrail/AuditReportResource.<lang>.resx` in
ONLYOFFICE/CommunityServer at commit `fe1fa7babd093969e939ba6ff45a9fee1299dc93` against the
neutral `AuditReportResource.resx` (478 entries). The 0.7.2 checker ran on the same parsed
entries as a baseline. The job's output is in [stdout.txt](stdout.txt), unedited; the
per-language table is in [onlyoffice_audit.csv](onlyoffice_audit.csv) and
[onlyoffice_audit.json](onlyoffice_audit.json).

## Predictions

| | Prediction | Result | Value |
|---|---|---|---|
| P1 | ja: at least 150 keys get a `lookalike-brace` error | HELD | 199 keys (242 errors) |
| P2 | the 23 languages other than ja, zh-CN, zh-TW: no `lookalike-brace` issue | HELD | 0 |
| P3 | zh-CN and zh-TW: fewer than 10 keys with a `lookalike-brace` error, each | HELD | 0 and 0 |
| P4 | ja: fewer than 20 keys still get `placeholder-missing` from 0.8.0 | HELD | 3 |

All four held.

## What it shows

- **Japanese only.** 203 of the 442 Japanese values contain a fullwidth brace; no value in any
  other language does, Chinese included. The Japanese values write `{0}` as `｛０｝` (fullwidth
  braces and fullwidth digits), so .NET's `string.Format` prints the text as written and the
  name, file or user that the audit message is about is never shown.
- **None are half-converted.** 0 errors were of the "one brace still ASCII" kind (`｛0}`), the
  form that makes .NET throw. These messages lose their values; they do not crash.
- **Same keys, better diagnosis.** 0.7.2 already flagged 202 Japanese keys, as a generic
  `placeholder-missing`. 0.8.0 flags the same number of keys (202 -> 202): 199 now say which
  character is wrong, and 3 remain `placeholder-missing` for some other reason. In the other 25
  languages the error counts are identical between the two versions, so the new rule changed
  nothing where it should not.
- So the value of 0.8.0 here is the message, not detection: a translator is told that `｛０｝`
  must be typed `{0}`, rather than that `{0}` is missing.

## Limits and open ends

- One project, one resource file. This tests the checker and measures one known case; it is not
  a census of .resx files ([FORMATS.md](../FORMATS.md) has the cross-format counts).
- 203 Japanese values have a fullwidth brace but 199 keys get an error. The job also reports 3
  `lookalike-brace` warnings (a fullwidth copy next to a real placeholder). The job did not list
  those keys, the 3 remaining `placeholder-missing` keys, or the one value left over, so they are
  not explained here.
- Other languages have their own `placeholder-missing` errors (Ukrainian 7 keys, Portuguese
  (Brazil) 4, Turkish, Hungarian and Vietnamese 3 each, and so on), which 0.7.2 also reports. They
  are not about braces and were not examined.
- The checker's verdict comes from reading the files. ONLYOFFICE's software was not run, and the
  call sites were read for the cases in [BRACES.md](../BRACES.md) only.
