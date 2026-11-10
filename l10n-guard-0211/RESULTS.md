# Results: l10n-guard 0.21.1 check (pre-registered)

Graded 2026-11-10 against [PREREG.md](PREREG.md) (marker "l10n-guard 0.21.1 PREREG v1", sha256
6a6d704bf8b34c50801eece0367eb7875d5e8b936128dd501047515f739d76bf, checked by the job before it
read any repository). The job's raw output is unchanged in this folder:
[summary.json](summary.json), [report.txt](report.txt), [compare.csv](compare.csv) and
[patch.diff](patch.diff). The job, guard-0211-v1, ran on 2026-11-10 from 21:40 to 21:43 UTC.
AI agents working for MV2 of Munim, Inc. did the checking; no project maintainer reviewed it.

## Verdicts

| Prediction | Verdict |
|---|---|
| T: every test module passes after the change, including test_0211 | **HELD** (23 of 23 modules) |
| A: test_0211's two Action tests run and pass | **HELD** (7 tests ran, 0 skipped) |
| S: same (code, language) findings as 0.21.0 on every folder read | **HELD** (18 of 18 folders) |
| M1: Tootle `nb-NO` message says "rename po/nb-NO.po to po/nb_NO.po" | **HELD** |
| M2: NetworkManager-openconnect `en_US` message says "never compile or install it" | **HELD** |
| M3: Meson findings without a hyphen keep their message byte for byte | **HELD** (20 of 20) |

All six held, so the release rule says to release l10n-guard 0.21.1.

## Negative and weak results first

- **This check says nothing new about precision.** It tests messages and the Action wiring only.
  The same files are reported as in 0.21.0, so that release's precision result still applies:
  5 of 6 sampled findings were real, one of them borderline. The release does not fix the known
  false finding: gnome-terminal's `mjw.po`, which was left out of `LINGUAS` on purpose. That
  case is now the subject of a separate pre-registered census
  ([pyhdr/PREREG.md](../pyhdr/PREREG.md)).
- **The rename advice is mechanical.** It turns `-` into `_`. That gives the right gettext name
  for `nb-NO`, `pt-BR` and `zh-Hant`, but not for script subtags gettext writes as modifiers.
  `sr-Latn` should become `sr@latin`, and 0.21.1 would suggest `sr_Latn`. No such file was in
  the 18 folders. The earlier write-up suggested `nb.po` for Tootle; 0.21.1 suggests `nb_NO.po`.
  Both are found in a normal `nb_NO.UTF-8` locale, and `nb` also covers a bare `nb`.
- **Three lines still name 0.21.0** after the version bump (see the job's `still-0210.txt`). All
  three are history: the README's feature list and results link for the 0.21.0 `linguas` kind,
  and a section comment in `l10n_guard.py`. That is intended.
- **The Action tests need bash and python3.** They would be skipped on a machine without them.
  In this job both were present, so they ran (0 skipped).

## What changed in 0.21.1

- `linguas-unlisted` on a file named with a hyphen now says to rename it to the gettext
  spelling and list that. A catalog installed as `nb-NO` is never looked up.
- Autotools messages read "gettext's build rules never compile or install it" (was "compiles").
  Meson messages are unchanged.
- The GitHub Action passes only `target` to the project-folder kinds `locale-config` and
  `linguas`, so `uses: munimtechnologies/l10n-guard@v0.21.1` with `kind: linguas` and
  `target: .` now works. Before, those kinds had to run as a plain step.

The full diff is in [patch.diff](patch.diff). The released files are the job's `pkg/` output,
unchanged.

Text and data: CC BY 4.0. Code: Apache-2.0. Made with AI agents by MV2 of Munim, Inc.
(mv2@munimtech.com).
