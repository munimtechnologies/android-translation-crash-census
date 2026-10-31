# Results: where stray zero-width spaces in Weblate-managed apps came from

Graded 2026-10-31 by AI agents working for MV2 of Munim, Inc. Pre-registration: [PREREG.md](PREREG.md) (marker "weblate-origin PREREG v1", public before the job read any history; the job recorded its SHA-256, `ab241ee2...`). Code: `zwsp_origin.py` 0.1.0, unchanged. Job `weblate-origin-v1` ran 2026-10-31 08:34-08:46 UTC: its 16 offline tests passed, then it read 23 repositories in 9.5 minutes. Licence: Apache-2.0 (code), CC BY 4.0 (text and data).

## Pre-registered verdicts (copied unchanged from `summary.json`)

| | Prediction | Result | Verdict |
|---|---|---|---|
| Gate | at least 60 attributed rows from at least 15 repositories | 90 rows from 23 repositories, all attributed | met |
| P1 | fewer than half of the rows were introduced by a Weblate commit | **0 of 90** (share 0.0) | **HELD** |
| P2 | at least half of the non-Weblate rows arrived with the string (`folder-created` or `key-added`) | 85 of 90 (24 folder-created, 61 key-added, 5 edited) | **HELD** |
| P3 | P1 holds when any one repository is left out | share 0.0 in all 23 subsets | **HELD** |

All 23 repositories cloned, every census head was found, and all 90 rows were still present at the census head, so nothing was dropped.

**In short:** in the apps the census classed as translated on Weblate, not one of the 90 shipped strings whose only stray character is U+200B got it from a Weblate commit. Each one came in through some other kind of commit, and almost always (85 of 90) in the commit that added the string or the whole language folder, not as a later edit of an existing translation.

That fits what Weblate's source suggests (see PREREG.md): its `RemoveZeroSpace` fixup cleans text saved through Weblate, while text that reaches Weblate from the repository is parsed without fixups and left as it is (it is flagged by the `zero-width-space` check, not changed). It is also the other half of the census's earlier result that Weblate repositories ship about a quarter as many stray U+200B as other repositories ([hidden-chars RESULTS](../RESULTS.md)): the ones that remain seem to have come in around Weblate, not through it. This is how Weblate is designed to work, not a Weblate bug.

## What the introducing commits were (exploratory, not pre-registered)

Everything below was tallied by hand from the first lines of the commit messages in [`rows.csv`](rows.csv), after the verdicts were known. Check it against that file. A follow-up job (`weblate-control-v1`, below) recounts the platform names by code from the full commit messages.

| Kind of introducing commit | Rows | Apps |
|---|---|---|
| Ordinary commits by the project or its contributors that add or complete translations (for example "Added initial support for 9 new languages", "i18n: synchronize and complete full translations for all 51 supported languages", a release commit) | 46 | 9 |
| Commits whose message names another translation platform: Localazy 9, Crowdin 7 (6 of them Crowdin's default "New translations strings.xml (Language)" message), Transifex 5 | 21 | 7 |
| Commits that bring in code from another project (bitmask_android updating ics-openvpn and its submodules, or "update dependencies") | 12 | 1 |
| Moves, refactors, a branch cherry-pick and first or initial-release commits (the U+200B is older than this commit, and its real origin was not traced) | 8 | 6 |
| "Sync Strings" commits in a fork of Element X whose message names no platform | 2 | 1 |
| A hand-written commit, "quality suggestions from weblate", that edited an existing translation (not a Weblate commit) | 1 | 1 |
| **Total** | **90** | **23** (two apps appear in two lines) |

Other exploratory numbers from `summary.json`:

- Commit years: 50 of the 90 introducing commits are from 2026; 39 of those 50 are ordinary translation commits in five apps (Episteme 14, Feedora 12, LeanType 6, Rhythm 6, curbox 1). The commit messages don't say how those translations were produced, so nothing is claimed about it here.
- Pair-shaped rows ("space + two U+200B", as in [zwsp-signature](../zwsp-signature/ZWSP-SIGNATURE.md)): 75 of 90, Weblate share 0 of 75; other rows: 0 of 15.
- Forks: two Mastodon-app forks (moshidon and seqular) share the same 3 upstream Crowdin commits, and ArcaneChat is a fork of Delta Chat with the same string. Without those 4 duplicated rows, 86 rows remain, still 0 from Weblate.
- Four apps hold 50 of the 90 rows (Episteme 14, bitmask_android 13, Feedora 12, SchildiChat Next 11; see `per_repo_rows_weblate`). P3 was there for this, and it held.

## Control, queued (exploratory)

"0 of 90" only means something if Weblate commits do exist in these histories and the classifier finds them. The census put these repositories in the Weblate group because their history has commits by Weblate (by name, email or the "using Weblate" message), but this job did not count them itself. A follow-up job, `weblate-control-v1` ([`control.py`](control.py), tests in `test_control.py`), downloads the published `zwsp_origin.py` unchanged and counts, for the same rows: Weblate commits in each repository and in each row's language folder; Weblate commits to that folder made after the U+200B arrived (which it survived); and which platform, if any, each introducing commit's full message names. It was written after these results were seen, so it is exploratory. Its numbers will be added here when it finishes.

## Limits

- "Introducing commit" means the newest commit that put U+200B into the string. For the 8 move, refactor and first-commit rows, and for code brought in from another project, the U+200B is older and its real origin wasn't traced.
- The Weblate test is the commit message ("using Weblate" or a `Translate-URL:` trailer) or a `@weblate.org` email. A Weblate set up to write different commit messages would be missed. The control job checks how often the rule fires in these repositories.
- Platform names in commit messages are what the committer wrote, not proof of where the text was made.
- 90 rows in 23 apps, with a few apps holding most of them. The census labelled these apps Weblate from their commit history, not by asking the projects.

## Files

- [`PREREG.md`](PREREG.md), [`zwsp_origin.py`](zwsp_origin.py), [`test_zwsp_origin.py`](test_zwsp_origin.py): the pre-registration and the code that was run.
- [`summary.json`](summary.json): the job's output, with the verdicts, the hits.csv SHA-256 and the per-repository counts.
- [`rows.csv`](rows.csv): one row per string with the introducing commit, its date, kind and first message line (no author names or emails).
- [`repos.jsonl`](repos.jsonl): clone status and time per repository.

Made with AI agents. MV2, Munim, Inc., mv2@munimtech.com
