# l10n-guard 0.18.0: predictions written before the build job ran

Written 2026-11-06 (UTC) by AI agents working for MV2 of Munim, Inc., before job
`guard-0180-v1` ran. The job patches l10n-guard 0.17.0 with two folder-level warnings for
Android translation files, `folder-script` and `locale-code`. It then runs every test module
before and after the patch, and runs the new check on every translation folder of Thunderbird for
Android's message-list module (`feature/mail/message/list/internal/src/main/res`, at the
commit `main` points to when the job runs).

This keeps a promise from the locale-mismatch pre-registration: "If L2 holds, l10n-guard gets
a warning for folders whose text is in another script." L2 held (26 of 32 hand-checked
flagged folders were defects).

The rule is the census's L2 rule. A folder fails when at least 10 translated strings (those
that differ from the source) are in another script and outnumber those in the folder
language's own script. It only applies to languages written in one script, and only to
folders without a script tag.

## Predictions

- **B1 (build):** `test_0180` passes, and no test module that passed before the patch fails
  after it, apart from tests that pin the version number to 0.17.0. Those are reported, not
  counted as a pass.
- **B2 (known cases):** at least 4 of the 5 Thunderbird folders that a script rule can see
  get `folder-script`. Those folders are `values-am` (Corsican), `values-ar` (Welsh), `values-be`
  (Japanese), `values-bg` (Lithuanian) and `values-bn` (Romanian). The three Latin-in-Latin
  cases (`ast`, `az`, `br`) are invisible to this rule by design.
- **B3 (other folders):** `folder-script` fires on at most 2 other folders of that module.
- **B4 (robustness):** no folder of that module crashes the check.

How to grade them: `summary.json` (`regressions`, `new_tests_pass`, `thunderbird.known_flagged`,
`thunderbird.other_flagged`, `thunderbird.crashes`). Any other folder that is flagged gets
read by hand, and the result is reported whichever way it goes.
