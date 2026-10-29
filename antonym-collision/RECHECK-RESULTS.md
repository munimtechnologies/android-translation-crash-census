# Mattermost re-check: are the 67 antonym collisions still there?

MV2 of Munim, Inc., with AI agents, 2026-10-29. Text and data: CC BY 4.0. Code: Apache-2.0.

## What was run
The sealed job `mm-recheck-v1` (code in [recheck/](recheck/), 12 offline tests passed) loaded
l10n-guard 0.14.0 (sha256 7d12df8c469090ae...), took the 67 Mattermost rows from
[formatjs-results/warnings.csv](formatjs-results/warnings.csv) (found at `be207f89`, 2026-10-20) and
read Mattermost's webapp catalogs on `master` at `b9fd23e542a2f544033e2b385313bc43ab18e490`
(downloaded 2026-10-29 02:18 UTC; 29 i18n files, 27 locales compared, none unparsed).

For each row it records whether both keys still share the 2026-10-20 value. For each key it also lists
how the SAME catalog translates that key's English text under other keys ("the catalog's own wording"),
so a fix can reuse wording the project already ships. Descriptive only; nothing here was
pre-registered. The job was filed on 2026-10-28 ~14:35 UTC and waited about 12 hours for shared
compute.

Raw output: [recheck-results/](recheck-results/) (`recheck.csv`, `summary.json`, `stdout.txt`).

## Result
- **67 of 67 rows are still present, unchanged** (0 changed, 0 gone). l10n-guard finds no new
  antonym collisions on master (67 warnings, the same 67).
- Mattermost's AI translation pipeline (since v12.0) has filled in new strings since 2026-10-20 but has
  not touched these. Together with [PROVENANCE-RESULTS.md](PROVENANCE-RESULTS.md) and
  [PROVENANCE-DROPPED-RESULTS.md](PROVENANCE-DROPPED-RESULTS.md) (all 67 predate the pipeline), this
  fits the earlier reading: a pipeline that reviews only its own new output does not revisit them.
- Spot-check outside the job (read through a summarising web fetch, so not byte-verified): the four
  Italian wrong strings are also in the **v12.0.1** release catalog (`channel_header.unarchive` and
  `api.channel.restore_channel.unarchived` read as "archive").

## Graded fix list
[recheck-fixes.csv](recheck-fixes.csv) turns the 67 pair rows into **65 distinct keys** that need new
text (one row per key: locale, key, English, current value, problem, proposed value, where it came
from). Grades are by AI agents, not native speakers.

| problem | keys | what it means |
|---|---:|---|
| opposite | 27 | the key shows the opposite action (e.g. Unarchive shown as Archive, Unmute as Mute, public as private) |
| wrong status / field | 6 | Korean status prompts naming the wrong status; Polish LDAP first/last name both said "username" |
| shared | 32 | two different options share one label (mostly the old "Convert Channels" label kept on both "Convert to public" and "Convert to private" in 10 locales; Romanian "Nume" on first-name keys) |

**13 of the 65 keys can be fixed with wording the same catalog already uses** for the same English
(column `proposed_from` names the source key), for example Czech `channel_header.unarchive` ->
"Zrušit archivaci kanálu" and Brazilian Portuguese's two permission names -> "Converter em público" /
"Converter para privado". The other 52 have no such wording in their catalog and need a speaker
(or the project's pipeline) to supply it; the list leaves those blank rather than inventing text.

By locale (keys): ko 12, ro 5, pl 5, cs 4, it 4, pt-BR 4, sv 4, vi 4, bg 3, es 3, fa 3, fi 3, hr 3,
lt 3, zh-TW 3, nl 1, tr 1.

## Limits
- One project, one checker. Recall is unknown: l10n-guard only sees pairs whose English differs by an
  antonym and whose translations are identical.
- Grading is by AI agents reading the catalogs, not native speakers, and nothing was run in a live
  Mattermost server. Six Korean status strings and the Romanian "Nume" rows rest on that reading.
- "Catalog's own wording" means another key with the same English (case, spacing and trailing
  punctuation ignored); context can still differ (a menu item vs. a title).

## Reproduce
```
cd antonym-collision/recheck
python -m unittest -v test_mm_recheck
python mm_recheck.py --out-dir out
```
Needs network (raw.githubusercontent.com, codeload.github.com). The output reflects whatever
`master` is when you run it.
