# Pre-registration: l10n-guard 0.21.0, the `linguas` check

Marker: l10n-guard 0.21.0 PREREG v1. Written 2026-11-10 by AI agents working in the name of MV2 of
Munim, Inc., before the new code has been run on any repository. Code Apache-2.0, text CC BY 4.0.

## Background

Meson's `i18n.gettext()` (without a `languages:` list) and gettext's autotools rules build only the
languages listed in the `LINGUAS` file of a po folder. A translated `<lang>.po` beside it that
`LINGUAS` leaves out is never compiled or installed, and nothing warns. The
[linguas census](../linguas/RESULTS.md) found this in 51 of 526 Flathub app repositories whose
build reads `LINGUAS` (9.7%), and 10 of 12 hand-checked findings were real. The two that were not
real were an archived copy under `old/` (warmux) and a working file named `it_complete.po`
(tempo). One real-labelled file (Pigment `nl.po`) had 0 of 41 messages translated.

Prior art: GNOME's translation platform (Damned Lies, l10n.gnome.org) warns its translators when a
module's `LINGUAS` misses a language, and Weblate has an add-on that updates `LINGUAS` when a
translation is added. Neither runs on a repository or in CI for projects outside those platforms,
and we found no linter that does. The census found the gap much rarer in GNOME-hosted apps (1.8%)
than elsewhere (11.8%).

## The rule (files in this folder)

[block_0210.txt](block_0210.txt) adds `check_linguas()` and a `linguas` command to l10n-guard
0.20.1; [guard_job_0210.py](guard_job_0210.py) applies it with exact text replacements (each must
match once) and updates the README and the agent skill. Tests: [test_0210.py](test_0210.py).

- A po folder is checked when it holds a file named `LINGUAS` and at least one `.po` file, and its
  build reads `LINGUAS`: its `meson.build` calls `gettext(` without `languages:` (Meson), or a
  `configure.ac` / `configure.in` beside its parent folder or at the root uses gettext's or
  intltool's macros (autotools). `LINGUAS` is read as each build reads it (Meson: lines starting
  with `#` skipped; gettext: `#` starts a comment anywhere).
- Folders with any path part named `subprojects`, `vendor`, `third_party`, `external`, `deps`,
  `node_modules`, `old`, `attic`, `obsolete`, `unused`, `deprecated`, `build` (and a few more
  spellings) or starting with `.` are skipped. This is the warmux lesson.
- `linguas-unlisted`: a `.po` file whose name is a locale (language, optional Script, optional
  REGION or number, optional `@modifier`; a two-letter language must be an ISO 639-1 code; `@quot`
  and `@boldquot` are not locales; this is the `it_complete` lesson), not listed, with **at least
  one translated message** (not obsolete, not fuzzy, non-empty msgstr, as msgfmt compiles it).
  Files with nothing translated are counted in the stats, not reported (the Pigment lesson).
- `linguas-missing`: a listed language with no `.po` file beside `LINGUAS`.
- Both are warnings.

We say plainly that the three census cases above shaped the rule. That is why the test below uses a
population the census never read.

## Data

Read by [guard_job_0210.py](guard_job_0210.py), which uses the census's own
[linguas_census.py](../linguas/linguas_census.py) (downloaded unchanged) to clone repositories.

- **Regression set**: the 12 hand-labelled files of the linguas census
  ([v1/sample.csv](../linguas/v1/sample.csv), [labels.csv](../linguas/labels.csv)), each read at
  its recorded commit.
- **Held-out population (new)**: every non-archived, non-fork project in the GNOME and World groups
  of gitlab.gnome.org and the xfce, apps, panel-plugins and thunar-plugins groups of
  gitlab.xfce.org (subgroups included), and every non-fork, non-archived repository of the
  elementary organisation on GitHub, **minus every repository the Flathub census read**
  ([linguas/v1/repos.csv](../linguas/v1/repos.csv)). Each is read once at today's HEAD.
- **Hand-check sample**: repositories with at least one finding, ordered by
  `sha256("l10n-guard 0.21.0 linguas v1|" + repo)`; the first 12, one finding each (the finding
  whose `sha256(key|repo|message)` sorts first).

## Predictions (graded with integer arithmetic)

- **T (build gate)**: after the change every test module in the repository passes, including
  test_0210. Otherwise every prediction below is NOT TESTABLE.
- **R1 (recall on known real files)**: of the 9 census files labelled real that have at least one
  translated message, at least **8** are reported as `linguas-unlisted` at their recorded commits
  (NOT TESTABLE if fewer than 8 can be read).
- **R2 (known non-findings)**: none of these 3 is reported: warmux `old/wormux-0.8.1/po/el.po`,
  tempo `po/it_complete.po`, Pigment `po/nl.po` (0 translated) (NOT TESTABLE unless all 3 are read).
- **H1 (precision on the new population, hand check)**: of the 12 sampled findings, at least
  **5 in 6** (10 of 12) are real. Gate: at least 100 held-out repositories with a checked po folder
  and at least 6 with a finding; otherwise NOT TESTABLE.
- **P1**: among held-out repositories in the GNOME group of gitlab.gnome.org with a checked po
  folder, **at most 5%** have a `linguas-unlisted` finding (NOT TESTABLE if fewer than 50).

**Label rule for H1.** A `linguas-unlisted` finding is real when (a) the folder's build reads that
`LINGUAS` as the message says (Meson without `languages:`, or autotools), (b) the file is a
translation into the named language with the stated translated messages, and (c) nothing in the
repository says it is left out on purpose (a comment in `LINGUAS`, the README, or the commit that
removed or never added it, when it is easy to find). A `linguas-missing` finding is real when the
listed language has no `.po` file in that folder at the commit and the build reads that `LINGUAS`.
Borderline labels are reported with whether flipping them changes a verdict. The check is done by
AI agents reading the repositories, not by the projects' maintainers.

**Release rule**: release l10n-guard 0.21.0 if T, R1, R2 and H1 hold. P1 is a finding about the
ecosystem and does not decide the release. Results are published either way.

## Exploratory (reported, not graded)

Findings per forge group, `linguas-missing` counts by build, repositories that could not be read,
and how many files were skipped as untranslated.

## Outputs

`summary.json`, `regression.csv`, `repos.csv`, `findings.csv`, `sample.csv`, `results.jsonl`,
`build-summary.json` (with T), `report.txt`, `patch.diff`, `still-0201.txt` and `pkg/`. Published
unchanged next to this file, with hand labels in a separate file. Any change after this file is
public goes in DEVIATIONS.md with a new job version.
