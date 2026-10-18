# Pre-registration: l10n-guard 0.8.0 on ONLYOFFICE's audit-trail translations

Written 2026-10-18 (~10:30 UTC), before the run. Made by MV2 of Munim, Inc. with AI agents.
Text licensed CC BY 4.0; code Apache-2.0.

## What will run

l10n-guard 0.8.0 adds two things: a `lookalike-brace` rule (a `{0}`, `{name}` or `{{name}}`
written with the fullwidth braces ｛ ｝, U+FF5B and U+FF5D, often with fullwidth digits, as in
`｛０｝`) and a reader for .NET `.resx` files. A queued compute job (`l10n-guard-080-v1`) builds it
from 0.7.2, runs every test, and then checks every translation of ONLYOFFICE Community Server's
audit-trail messages:

- files: `module/ASC.AuditTrail/AuditReportResource.<lang>.resx`, 26 languages, against the
  neutral `AuditReportResource.resx`
- pinned commit: `fe1fa7babd093969e939ba6ff45a9fee1299dc93` (ONLYOFFICE/CommunityServer, 2026-05-05)
- the 0.7.2 baseline is run on the same parsed entries, so verdicts can be compared key by key

[BRACES.md](BRACES.md) estimated about 200 Japanese audit messages with fullwidth braces
from a code search. This run counts them with the checker itself, across all languages.

## Predictions

- **P1** ja: at least 150 keys get a `lookalike-brace` error.
- **P2** the 23 languages other than ja, zh-CN and zh-TW: no `lookalike-brace` issue at all
  (error or warning).
- **P3** zh-CN and zh-TW: fewer than 10 keys with a `lookalike-brace` error, each.
- **P4** ja: fewer than 20 keys still get `placeholder-missing` from 0.8.0 (that is, the
  fullwidth braces explain nearly all of the lost placeholders).

Each will be reported as HELD or FAILED, with the per-language table and the job's output
unedited. A failed prediction is published as failed.

## Limits

One project, one resource file. It tests the checker and measures one known case. It is not a
census of .resx files. Nothing is run against ONLYOFFICE's software; only its public
translation files are read.
