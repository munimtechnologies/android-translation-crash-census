# Pre-registration: translations left out of `po/LINGUAS` in Flathub apps' source code

Marker: linguas census PREREG v1
Written 2026-11-09 by AI agents working for MV2 of Munim, Inc. (mv2@munimtech.com), before any
repository in the population is read. Code: `linguas_census.py`, tests: `test_linguas_census.py`
(same folder, same commit). Licence: Apache-2.0 (code), CC BY 4.0 (text and data).

## Question

Many Linux desktop apps keep their translations as gettext files `po/<lang>.po` next to a file
`po/LINGUAS` that lists the languages to build. Meson's `i18n.gettext()` reads that list when no
`languages:` argument is given and makes a build target only for each listed language
(`mesonbuild/modules/i18n.py`: `for l in languages:` ... `l+'.po'`; the list comes from
`read_linguas()` in `mesonbuild/scripts/gettext.py`). gettext's autotools rules (`po.m4`) also
take `ALL_LINGUAS` from `po/LINGUAS`. So a `<lang>.po` file whose language is not in LINGUAS is
never compiled or installed: the translation is in the repository, but users of that language see
English. Meson prints nothing about it. The opposite slip, a listed language with no `.po` file,
stops `meson setup` with "File xx.po does not exist" (mesonbuild/meson#12368), so it is found at
once.

Prior art. GNOME's translation site (l10n.gnome.org, "Damned Lies") shows a per-module warning,
'The language "xx" is not listed in the LINGUAS file for the domain "po"', to the translators of
modules it hosts. Weblate has an add-on, "Update LINGUAS file" (`weblate.gettext.linguas`), that
keeps the list in step when a project installs it. We found no count of how often the slip ships
across apps outside one platform, and no stand-alone check for it in a general translation linter.

## Population

Every app listed by the Flathub API (`https://flathub.org/api/v2/appstream`) when the job runs. For
each app, its metadata (`/api/v2/appstream/<id>`) gives `urls.vcs_browser`; if that is missing or
not on a supported host, `urls.homepage` is used if it is a repository page. Supported hosts:
github.com, codeberg.org, bitbucket.org, git.sr.ht (owner/name) and the GitLab hosts gitlab.com,
gitlab.gnome.org, invent.kde.org, framagit.org, gitlab.freedesktop.org, salsa.debian.org,
gitlab.xfce.org (path up to `/-/`). URLs are deduplicated without regard to case. Each repository
is read once at its default branch's HEAD (blobless depth-1 clone; files read on demand). The
Flathub list has no commit id, so its SHA-256 and the run date are recorded.

Translate group: from `urls.translate` of the repository's apps: **gnome** if any points to
l10n.gnome.org, else weblate (host contains "weblate"), crowdin, transifex, other, or none.

## Definitions (as coded)

- **LINGUAS directory:** a directory, not under subprojects, vendor(s), third_party, thirdparty,
  third-party, 3rdparty, external(s), deps, node_modules or submodules, that holds a file named
  `LINGUAS` and at least one `.po` file directly in it. At most 20 per repository.
- **Build:** **meson** if that directory's `meson.build` calls `gettext(` and has no `languages:`;
  **meson-explicit** if it has `languages:` (not graded: LINGUAS is not read); **autotools** if
  not meson and the `configure.ac`/`configure.in` in the directory's parent or at the root uses
  `AM_GNU_GETTEXT`, `IT_PROG_INTLTOOL`, `AC_PROG_INTLTOOL` or `AM_GLIB_GNU_GETTEXT`; else **other**
  (not graded). **Governed** = meson or autotools.
- **Listed languages:** parsed the way the build reads LINGUAS (Meson: lines starting with `#`
  skipped, the rest split on whitespace; autotools: `#` starts a comment anywhere).
- **Dropped file:** a `<stem>.po` in a governed directory whose stem looks like a language
  (`^[A-Za-z]{2,3}([_-][A-Za-z0-9]{2,8})*(@[A-Za-z]+)?$`, not ending `@quot`/`@boldquot`) and is
  not exactly a listed language.
- **Phantom:** a listed language with no `<lang>.po` in the directory.
- **Governed repository:** has at least one governed LINGUAS directory. **Flagged:** a governed
  repository with at least one dropped file.
- **Substantive:** a dropped file (up to 10 read per directory) in which at least half of its
  messages (non-empty msgid; header and obsolete `#~` entries skipped) are translated (not fuzzy,
  some msgstr non-empty), which is what `msgfmt` compiles by default. Unknown if unreadable or
  empty.

## Control (before any population repository is read)

GNOME Calculator (gitlab.gnome.org/GNOME/gnome-calculator) must show `po/` as a meson LINGUAS
directory listing `de`, and `po/de.po` must read as substantive with at least 100 messages. If not,
the job stops (exit 3) and nothing is graded.

## Gate

At least 1,000 repositories read and at least 150 governed repositories. If not, P1-P4 are NOT
TESTABLE and no rate is claimed.

## Predictions (graded by code, integer arithmetic)

- **P1.** Between 3% and 25% of governed repositories are flagged
  (HELD if 100*k >= 3*n and 4*k <= n).
- **P2.** At least half of the dropped files with known content are substantive: real
  translations that ship unused, not empty stubs (testable with >= 4 such files).
- **P3.** Governed repositories in the gnome group (whose translators see Damned Lies' LINGUAS
  warning) are flagged at a strictly lower rate than the other governed repositories (testable
  with >= 20 in each and >= 4 flagged in all).
- **P4.** In meson directories, the slip nothing reports is commoner than the slip that breaks
  `meson setup`: fewer repositories have a phantom than a dropped file (testable with >= 4
  repositories having either).

## Hand check (H1, next run, before any claim of precision)

Up to 12 flagged repositories, chosen by SHA-256 of "linguas census v1|<repo>", one dropped file
each (also by hash), listed in `sample.csv`. Each is read at the recorded commit and labelled
**real** when (a) the file is a translation of this directory's gettext domain, (b) the build that
ships the app reads this LINGUAS for the directory (Meson `gettext()` without `languages:`, or
gettext/intltool autotools rules, and the Flathub manifest builds with that system), (c) nothing
else compiles or installs the file (a custom script, CMake rule or packaging step), and (d) its
language is not listed. H1 holds if real*4 >= 3*checked, testable with at least 6 checked.
Borderline calls are reported.

## Exploratory (no predictions)

Rates by translate group (weblate, crowdin, none, ...); directories by build, including "other"
builds; dropped stems that differ from a listed language only by case or `-`/`_` (`pt-BR.po` vs
`pt_BR`); autotools phantoms; the most frequently dropped languages; the total number of
translated messages in dropped files.

## Limits stated now

- The build rules come from Meson's and gettext's source, not from building each app; a project
  may install translations another way (H1 checks this on the sample).
- One app store's view: Flathub over-represents GTK/GNOME apps, and only apps whose metadata
  names a repository on a supported host are included.
- HEAD only: a slip fixed since the last release still counts; one shipped in a release but fixed
  at HEAD does not.
- A dropped file may be dropped on purpose (an unfinished translation held back); the census
  cannot see intent. P2 measures how much is translated, not whether it was ready.

## What happens next

Results go to `linguas/RESULTS.md` with the job outputs unchanged under `linguas/v1/` and the hand
labels in a separate `labels.csv`. If H1 holds, l10n-guard gets a `linguas` check (a `.po` next to
LINGUAS but not listed, and a listed language with no file), and confirmed cases are reported
upstream one at a time, where each project's contribution rules allow it, saying the check was
made with AI agents.
