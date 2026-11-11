# Pre-registration: linguas-history v1

Were the translations that `LINGUAS` leaves out ever listed?

Written 2026-11-11 (UTC), before any repository history is read by this code. Made with AI
agents working in the name of MV2 of Munim, Inc. Code: Apache-2.0. Data and text: CC BY 4.0.

## Question

Meson's `i18n.gettext()` and gettext's autotools rules build only the languages named in
`po/LINGUAS`. Our earlier census (`linguas/`, linguas-census-v1) found 120 `.po` files in 51
open-source repositories that their folder's `LINGUAS` does not list, so they are never built.
That census looked at one snapshot. This study asks how those files got there: was the language
**never listed**, or was it listed once and then **lost**, and if lost, by what kind of commit?

We know of no earlier count of this. The `linguas-unlisted` check in l10n-guard 0.21 cannot
read history, and we found no study of `LINGUAS` lines lost in merges or edits.

## What we already know (stated so it cannot be counted as a prediction)

While preparing fixes we looked by hand at two rows of this population:

- `mijorus/collector` `tr`: added in 0383848, then dropped by merge commit f64926a while the
  merge placed `uk_UA` (a merge-resolution loss).
- `alainm23/byte` (now `ellie-commons/byte`) `tr`: added in d394cb3 (2019), then commit
  b9f4838 "Add Italian Translation" (2020) replaced the `tr` line with `it` (a replace loss).

Both are inside the population and will be counted like every other row.

## Population and method

- Rows: all 120 rows of linguas-census-v1 `out/dropped.csv`, copied unchanged as `dropped.csv`
  (sha256 printed in the job log). No row is removed, including ones that look intentional
  (`old/` folders, `en_US`, `it_complete`); they are reported, not excluded.
- For each repository: `git clone --filter=blob:none --no-checkout`. History is read up to the
  census commit in `dropped.csv` (or HEAD, flagged, if that commit is gone), so fixes made since
  (including our own pull requests) do not change the result.
- For each folder: every **first-parent** commit that changed `<dir>/LINGUAS`, oldest first,
  parsed as Meson does (whitespace-separated codes, `#` starts a comment).
- Class per row: `never` (code in no main-line version), `lost` (in some version, not in the
  census version), `listed` (in the census version; unexpected), `no-history`, `error`.
- For a lost row, the removal commit is the first main-line version after the last one that had
  the code. Its kind, first match wins:
  - `merge-resolution`: a merge commit where the merged branch still had the code, or the
    branch never had it while the main line did;
  - if the merge brought in a branch commit that dropped the code, that commit is classified
    and prefixed `branch:`;
  - `subject-removal`: the subject matches remove/drop/disable/delete/exclude/revert/
    incomplete/unmaintained/outdated;
  - `file-deleted`: `LINGUAS` itself was deleted;
  - `replace`: the same commit added a different code;
  - `bulk`: the same commit dropped 3 or more codes;
  - `other`.
- **Collateral** = `merge-resolution`, `replace` and their `branch:` forms (the code vanished
  while something else was being done). **Deliberate** = `subject-removal` and its `branch:` form.
- A removal **event** is one distinct (repository, folder, main-line removal commit); several
  codes dropped in one commit are one event.

## Predictions (fixed now)

- **G (gate):** at least 45 of the 51 repositories analysed and at least 105 of the 120 rows
  classified as `never` or `lost`. If G fails, no rate below is claimed.
- **P1:** among substantive rows (`substantive == yes` in the census) classified `never` or
  `lost`, the lost share is between 5% and 35% inclusive. (The two known cases alone are about
  3%, so P1 needs at least two more.)
- **P2:** at least half of the removal events are collateral.
- **P3:** at most one third of the removal events are deliberate.
- **H (hand check):** every removal event (or, if there are more than 15, the 12 with the
  smallest removal sha) is checked on the forge's commit page: the code is in the first
  parent's `LINGUAS` and not after the commit. H holds if at least 90% are confirmed.

Unscored, reported as found: never-listed share, losses among non-substantive (stub) rows,
event kinds, how many lost or never-listed codes are listed again at today's HEAD, and how long
each `.po` file existed before its code was lost.

## Reporting

Verdicts are written exactly as `summary.json` gives them and the hand check gives them;
negative results go first. Anything changed after this file is published is listed in
DEVIATIONS.md. If P2 holds and H holds, a git-history mode for l10n-guard's `linguas` check
(name the commit that dropped a code) will be proposed and pre-registered separately.
