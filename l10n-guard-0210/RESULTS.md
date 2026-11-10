# Results: l10n-guard 0.21.0 `linguas` check (pre-registered)

Graded 2026-11-10 against [PREREG.md](PREREG.md) (marker "l10n-guard 0.21.0 PREREG v1", sha256
138232833eba340b79c5a3d76af8b0a4564077bed4eb8c845650928dcc30617a, checked by the job before it
ran). The job's raw output is unchanged in this folder: [summary.json](summary.json),
[report.txt](report.txt), [findings.csv](findings.csv), [regression.csv](regression.csv) and
[sample.csv](sample.csv). The hand labels are in [labels.csv](labels.csv). AI agents working for
MV2 of Munim, Inc. did the checking; no project maintainer reviewed the labels.

## Verdicts

| Prediction | Verdict |
|---|---|
| T: every test module passes, including test_0210 | **HELD** (22 of 22 modules, 334 tests) |
| R1: at least 8 of the 9 real census files with translations reported | **HELD** (9 of 9; see deviation 1) |
| R2: warmux `el.po`, tempo `it_complete.po`, Pigment `nl.po` not reported | **HELD** (0 of 3) |
| H1: at least 5 in 6 sampled findings real | **HELD, on one borderline label** (5 of 6) |
| P1: at most 5% of checked GNOME-group repositories have `linguas-unlisted` | **HELD** (3 of 123, 2.4%) |

Under the release rule (T, R1, R2 and H1), l10n-guard 0.21.0 is released.

## Negative and weak results first

- **H1 depends on one borderline label.** If NetworkManager-openconnect's `en_US.po` were
  labelled not real, H1 would be 4 of 6 and would FAIL. It is labelled real (borderline): the
  build reads `LINGUAS`, the file is OpenConnect's US English translation, and the maintainer
  keeps updating it with no word about leaving it out. But the source text is British English
  and about 98% of its strings are identical copies, so shipping it would change only a few
  spellings. The Flathub census labelled Draughts' `en_US.po` the same way, so the label
  follows that precedent.
- **One finding is not real.** gnome-terminal took `mjw` (Karbi) out of `LINGUAS` on purpose in
  2022 (commit 576df156) because the file's Plural-Forms header is invalid. l10n-guard cannot see
  commit history. The SKILL.md already tells agents to run `msgfmt --check` first, and that
  catches this case.
- **One message gives the wrong fix.** Tootle's `nb-NO.po` is a real, complete Norwegian
  Bokmål translation that never ships. The message says to add `nb-NO` to `LINGUAS`, but a
  catalog installed under `nb-NO` is never looked up by glibc. The working fix is to rename the
  file to `nb.po` and list `nb`. A later version should name the gettext spelling for file
  names written with a hyphen.
- **The sample is 6, not 12.** Only 6 of 291 checked repositories had a finding (the gate
  needed at least 6). The pre-registration does not say what happens with fewer than 12, so H1
  is graded by its stated ratio, at least 5 in 6.
- **Small wording bug:** autotools messages read "gettext's build rules never compiles"; it
  should be "compile".
- **No `linguas-missing` finding at all** in 291 repositories, so this run says nothing about
  how precise that code is.

## Numbers

549 held-out repositories were read at HEAD (none from the Flathub census). 291 have a po
folder whose build reads `LINGUAS`.

| Group | Read | Checked | With `linguas-unlisted` |
|---|---|---|---|
| gitlab.gnome.org/GNOME | 246 | 123 | 3 |
| gitlab.gnome.org/World | 104 | 27 | 2 |
| github.com/elementary | 128 | 72 | 1 |
| gitlab.xfce.org (4 groups) | 71 | 69 | 0 |
| **All** | 549 | 291 | 6 (2.1%) |

The census of Flathub apps' own repositories found 51 of 526 (9.7%). Platform projects, most of
which translate through a hosted platform (GNOME's Damned Lies, elementary's Weblate, Xfce's
Transifex), slip far less often. The two populations differ in more than the platform, so this
is a contrast, not a causal estimate.

## How the 5 real files got left out (post hoc, not pre-registered)

- Resources `af_ZA.po` and Tootle `nb-NO.po`: the commit that added the file (a direct commit and a
  GitHub pull request) changed only the `.po` file.
- desktop-icons `ko.po`: added in 2021 by a direct commit, not by GNOME's translation robot,
  and no `LINGUAS` commit mentions Korean. The robot updated the file later, and it is still
  unlisted five years on.
- elementary flatpak-platform `sco.po`: created by Weblate's languages add-on. The project's
  Weblate does not update `LINGUAS`.
- NetworkManager-openconnect `en_US.po`: imported from another project's translations.

In 4 of the 5, the file came in by a route that skips the step where `LINGUAS` gets updated.
That is a pattern seen in 5 files, not a measured rate.

## Deviations

1. The job printed R1 as "8 of 8 reported, 8 read". Its grouping matched only rows labelled
   exactly `real`, so it missed Draughts `en_US.po` (labelled `real (borderline)`), which is one of
   the 9 files the prediction names. regression.csv shows it was reported, so R1 is 9 of 9. The
   verdict is the same either way.
2. The first run of this job (guard-0210-v1, earlier on 2026-11-10) was stopped by a SIGTERM
   while it waited for 0.20.1 to reach main. It was re-filed unchanged. The re-filed run downloads
   the four pre-registered files from this repository, so the code that ran is the published code.

Text and data: CC BY 4.0. Code: Apache-2.0. Made with AI agents by MV2 of Munim, Inc.
(mv2@munimtech.com).
