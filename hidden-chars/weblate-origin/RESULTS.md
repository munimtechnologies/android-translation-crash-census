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

Everything below was tallied by hand from the first lines of the commit messages in [`rows.csv`](rows.csv), after the verdicts were known. Check it against that file. The control job below recounts the platform names by code from the full commit messages.

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

## Control results (exploratory, not pre-registered)

"0 of 90" only means something if Weblate commits do exist in these histories and the same rule finds them. A follow-up job, `weblate-control-v1` ([`control.py`](control.py), tests in [`test_control.py`](test_control.py)), downloaded the published `zwsp_origin.py` unchanged and ran it again on the same 90 rows, counting Weblate commits as well. It was written after the results above were seen, so it is exploratory. It ran 2026-10-31 09:21-09:28 UTC; its tests passed, all 23 repositories cloned, and all 90 rows were attributed again, with the same split of kinds (24 folder-created, 61 key-added, 5 edited).

| Check | Result |
|---|---|
| Repositories with at least one Weblate commit (same rule as P1) on the branch read | **23 of 23** |
| Weblate commits found in those 23 histories | 12,607 (5 to 3,027 per repository) |
| Rows whose language folder has at least one Weblate commit | 54 of 90 |
| Rows whose folder got a Weblate commit **after** the U+200B arrived, and still has it | 36 of 90, in 12 repositories |
| Platform named anywhere in the introducing commit's full message | none 66, Localazy 9, Crowdin 9, Transifex 5, "weblate" 1 |

What this shows:

- **The rule fires.** It finds Weblate commits in every one of these repositories, thousands in total, so "0 of 90" is not a detector that never matches. In 36 rows, Weblate went on to commit to the same language folder after the U+200B arrived, and the U+200B is still there. That fits Weblate leaving repository text alone, though a later Weblate commit to the folder need not have touched that string.
- **Platform names.** The code finds Crowdin in 9 introducing commits, 2 more than the hand count, because one Nym VPN cherry-pick commit names Crowdin only in the body of its message (2 rows). The single "weblate" match is the hand-written "quality suggestions from weblate" commit (Mental Math), which the P1 rule correctly did not count as a Weblate commit.
- Weblate hosts seen in commit trailers: mostly hosted.weblate.org, plus Codeberg's Weblate and several self-hosted instances. One repository (anonomi-android) has 503 Weblate commits but no `Translate-URL:` trailer, so no host is listed for it.

Files: [`control_summary.json`](control_summary.json), [`control_repos.csv`](control_repos.csv) (per repository: commits read, Weblate commits, first and last Weblate date, Weblate hosts), [`control_rows.csv`](control_rows.csv) (per row: introducing commit, kind, platform named, Weblate commits to the folder in total and after the U+200B arrived).

## Limits

- "Introducing commit" means the newest commit that put U+200B into the string. For the 8 move, refactor and first-commit rows, and for code brought in from another project, the U+200B is older and its real origin wasn't traced.
- The Weblate test is the commit message ("using Weblate" or a `Translate-URL:` trailer) or a `@weblate.org` email. A Weblate set up to write different commit messages would be missed. The control shows the rule finds Weblate commits in all 23 repositories, but it can't show how many it misses.
- Platform names in commit messages are what the committer wrote, not proof of where the text was made.
- 90 rows in 23 apps, with a few apps holding most of them. The census labelled these apps Weblate from their commit history, not by asking the projects.

## Files

- [`PREREG.md`](PREREG.md), [`zwsp_origin.py`](zwsp_origin.py), [`test_zwsp_origin.py`](test_zwsp_origin.py): the pre-registration and the code that was run.
- [`summary.json`](summary.json): the job's output, with the verdicts, the hits.csv SHA-256 and the per-repository counts.
- [`rows.csv`](rows.csv): one row per string with the introducing commit, its date, kind and first message line (no author names or emails).
- [`repos.jsonl`](repos.jsonl): clone status and time per repository.
- The control job's files, listed in the section above.

Made with AI agents. MV2, Munim, Inc., mv2@munimtech.com
