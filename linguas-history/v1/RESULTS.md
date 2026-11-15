# Results: linguas-history v1 (were the translations LINGUAS leaves out ever listed?)

Pre-registration: [PREREG.md](PREREG.md), written 2026-11-11 before any history was read. Job
`lhist-census-v1`, run 2026-11-15 (51 repositories, 120 rows from linguas-census-v1). The job's
output is published unchanged (`summary.json`, `rows.csv`, `events.csv`, `hand_check.csv`);
the hand check is in `labels.csv`. Made with AI agents by MV2 of Munim, Inc. Text CC BY 4.0,
code Apache-2.0.

## Negative result first

- **P2 FAILS.** We predicted that at least half of the removal events would be collateral (a
  language vanishing during a merge or while another line was edited). Only **3 of 10** were:
  one merge resolution (mijorus/collector `tr`) and two replacements (alainm23/byte `tr` -> `it`;
  planify `po/extra` `pt` -> `pt_BR`, which may itself be a deliberate rename).
- So, as pre-registered, **no git-history mode for l10n-guard is proposed.** Most unlisted
  translations were never listed, and most of the few removals were not accidents of merging.

## Verdicts

| Prediction | Result | Verdict |
|---|---|---|
| G: >= 45 of 51 repositories and >= 105 of 120 rows classified | 51 of 51; 120 of 120 | HOLDS |
| P1: lost share among substantive rows in 5%-35% | 5 of 67 = 7.5% | HOLDS |
| P2: collateral events >= half | 3 of 10 | **FAILS** |
| P3: deliberate events <= one third | 2 of 10 | HOLDS |
| H: >= 90% of removal events confirmed on the forge | 10 of 10 | HOLDS |

H was checked by hand on 2026-11-15 from each removal commit's diff (GitHub and GitLab commit
APIs; for one huge planify merge, `po/extra/LINGUAS` was read at the first parent and at the
merge). In every case the code was in the first parent's `LINGUAS` and gone afterwards.

## Descriptive (unscored, as pre-registered)

- 92 of 120 rows were **never** listed; 28 were listed once and **lost**. Of the 28 lost rows,
  23 are stubs (little or nothing translated) and 5 are substantive, in 5 repositories.
- Event kinds: other 2, replace 2, bulk 2, subject-removal 2, merge-resolution 1, branch:bulk 1.
- None of the 28 lost codes is listed again at today's HEAD; 1 never-listed code now is.

## Post-hoc reading of the 10 events (labelled post hoc, not part of any verdict)

Reading the diffs suggests that more of the removals were deliberate than the subject-line
rule could see: lifeograph's "updated translations." commented out most languages (incomplete
translations), and FocusTimer's "Review Flatpak manifest" cut 20 of 25 codes at once. Our
earlier lesson holds again: a translation left out of the build is often left out on purpose,
so a tool should report it with a question, not as an error. l10n-guard's `linguas-unlisted`
is already a warning that asks the maintainer to check first.
