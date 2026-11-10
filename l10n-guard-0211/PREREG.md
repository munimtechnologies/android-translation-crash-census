# Pre-registration: l10n-guard 0.21.1 (linguas advice, wording, Action support)

Marker: l10n-guard 0.21.1 PREREG v1. Written 2026-11-10, before the 0.21.1 code has run on
any repository. Code: [guard_job_0211.py](guard_job_0211.py) and [test_0211.py](test_0211.py)
in this folder. Made with AI agents by MV2 of Munim, Inc. Text CC BY 4.0, code Apache-2.0.

## Why

The [0.21.0 check](../l10n-guard-0210/RESULTS.md) found three things to fix:

1. For a file named with a hyphen (Tootle's `nb-NO.po`), `linguas-unlisted` said to add
   `nb-NO` to `LINGUAS`. A catalog installed under `nb-NO` is never looked up by glibc, so
   that advice does not help. 0.21.1 says to rename the file to the gettext spelling
   (`nb_NO.po`) and list that.
2. Autotools messages read "gettext's build rules never compiles or installs it". 0.21.1
   reads "never compile or install it". Meson messages do not change.
3. The GitHub Action passed a source and a target to every kind except four single-file
   kinds, so the project-folder kinds `locale-config` and `linguas` could not run through it.
   0.21.1 passes only `target` for them too.

No rule about which files are reported changes.

## What the job does

1. Waits until l10n-guard 0.21.0 is on main, downloads it, and runs every test module.
2. Applies the changes above (exact line replacements that must each match once; the three
   Action description edits are optional and logged if they do not match), bumps the
   version in `l10n_guard.py`, README.md and SKILL.md, adds `test_0211.py`, and runs every
   test module again.
3. Waits until this file is public. Then it reads 18 po folders at their recorded commits
   (the 6 held-out findings and the 12 regression files of the 0.21.0 check) and runs both
   0.21.0 and 0.21.1 `check_linguas` on each.

## Predictions

- **T:** every test module passes after the change, including test_0211. If not, the
  predictions below are NOT TESTABLE.
- **A:** test_0211's two Action tests run (not skipped) and pass. They run the Action's own
  bash step for `linguas` and `locale-config` with only `target` set.
- **S:** on every folder that can be read, 0.21.1 reports exactly the same (code, language)
  pairs as 0.21.0. NOT TESTABLE if fewer than 16 of the 18 folders can be read.
- **M1:** the Tootle `nb-NO` message contains "rename po/nb-NO.po to po/nb_NO.po".
- **M2:** the NetworkManager-openconnect `en_US` message contains "gettext's build rules
  never compile or install it".
- **M3:** every finding in a Meson-built folder whose file name has no hyphen has a message
  that is byte-for-byte identical in 0.21.0 and 0.21.1.

M1 and M2 are NOT TESTABLE if their folder cannot be read.

## Release rule

Release l10n-guard 0.21.1 if T, A, S, M1, M2 and M3 hold. Results are published either way,
and any later change goes in DEVIATIONS.md with a new job version.

## Limits

This check tests the messages and the Action wiring, not precision. Which files are reported
does not change, so the 0.21.0 precision result (5 of 6, one borderline) still applies.
