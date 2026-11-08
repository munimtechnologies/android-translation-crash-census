# Deviations from the pre-registration (l10n-guard 0.19.0 locale-config)

Written on 2026-11-08 (UTC) by AI agents working for MV2 of Munim, Inc., before any held-out
repository was read. Apache-2.0 (code) / CC BY 4.0 (text).

## 1. The build job was fixed and re-run (guard_job.py -> guard_job_v2.py)

**What happened.** The first job (`guard-0190-v1`, 2026-11-08 02:02-02:05 UTC) built l10n-guard
0.19.0 from the released 0.18.0 and ran every test module before and after the change. The new
unit tests (`test_0190`, 25 tests) passed, and so did every older module except one: `test_0180`
failed a single test, `Version.test_version`, which pins the version with
`self.assertEqual(g.__version__, "0.18.0")`. Because the job treats any failing older module as a
regression, it stopped as written ("the pre-registered tests are not run"), **before reading any
repository**. Its report and build summary are in [v1/](v1/).

**What changed.** `guard_job_v2.py` differs from `guard_job.py` in one step: it rewrites that one
line of `test_0180.py` to
`self.assertGreaterEqual(tuple(int(x) for x in g.__version__.split(".")), (0, 18, 0))`, the same
form `test_0170.py` already uses, and stops if the line is not found exactly once. (Inside the
job the file is named `guard_job.py`; its SHA-256 is printed with the others.) Every other
step, and every other test, is unchanged.

**What did not change.** PREREG.md, the check (`locale_config_block.txt`), its unit tests
(`test_0190.py`) and the prediction code (`holdout_0190.py`). The v2 job downloads all four from
the pre-registration commit `df139e9ef69f9a349a557f4c2be15c5a9d3ee2db` of this repository and
prints their SHA-256 before running. For comparison, the v1 job printed:

```
178dc9d52d8e025d067d686f80f5b0d810952492e6886abf9fe448e253e3d4bc  holdout_0190.py
0883b2e86e2bcbb0eec12e6f837b205d537fed104f3430aff63589e1535cc8a8  locale_config_block.txt
a1d42861c9ce93be425967a54ae1db4ae4a8c75c97d304d9da2812cced3d87c4  test_0190.py
1450ada379eb3ae6048cc49e85b64e32d8df6449278c709b2f2b3dfb56c0ba34  PREREG.md
```

The predictions, thresholds, sample keys and labelling rules are exactly as pre-registered. The
held-out repositories are still read at their HEAD on the day of the job, which is now the day of
the v2 job.

**Lesson.** A version-pinning test in an older module will fail on every release. Future build jobs
change such pins to a ">=" form as part of the version bump, and new test modules use the ">=" form
from the start.
