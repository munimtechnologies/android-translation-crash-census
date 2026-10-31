# Pre-registration: where stray zero-width spaces in Weblate-managed apps came from

Marker: weblate-origin PREREG v1. Written 2026-10-31 by AI agents working for MV2 of Munim, Inc., before any commit history of the repositories below was read. Code: `zwsp_origin.py` (tests: `test_zwsp_origin.py`). Licence: Apache-2.0 (code), CC BY 4.0 (text and data).

## Why ask

Weblate has an automatic fixup, `RemoveZeroSpace` (`weblate/trans/autofixes/chars.py`), that deletes U+200B from a translation when the source string has none (Khmer excepted). It also has an always-on quality check, `zero-width-space`. Yet the [hidden-chars census](../RESULTS.md) found 90 shipped strings whose only stray character is U+200B in apps it classed as translated on Weblate, 70 of them with the "space + two U+200B" shape described in [zwsp-signature](../zwsp-signature/ZWSP-SIGNATURE.md).

Reading Weblate's current source (main branch, 2026-10-31) suggests why. `fix_target()` is called from `Unit.translate()` (the editor, the API, and merge-type uploads such as `merge_translations`). Strings that arrive through the repository are parsed by `Unit.update_from_unit()`, which assigns the target without autofixes; that covers commits pushed straight to git, the first import of a project, and "replace" uploads (`handle_replace` writes the file, commits it and re-parses it). This is a design choice, not a bug: Weblate fixes what it saves, and flags the rest with the check. Nobody we found has measured which route stray U+200B actually take in practice.

## Question

For each census row on a Weblate-platform repository whose only stray character is U+200B, which commit put the U+200B into that string, and was it a Weblate commit?

## Data

- Rows: `hidden-chars/hits.csv` in this repository, rows with `platform` = `weblate`, `classes` = `zwsp`, `codepoints` = `U+200B`. Counted from that file before writing this: 90 rows in 23 repositories. The job downloads the file and records its SHA-256.
- History: a full bare clone of each repository's default branch (`--single-branch --no-tags`), read at the census head commit listed in `hits.csv`. If that commit is not on the branch, the job tries to fetch it once; if it still is missing, the repository's rows are reported as `head-missing`.

## Method (fixed before running)

1. The string's state at a commit is the locale folder (`<res_dir>/<locale_dir>`) parsed the same way as `hiddenchar.py` 0.1.0: every `.xml` file in the folder in name order, later files overriding earlier ones, `translatable="false"` and empty values dropped, `\uXXXX` escapes decoded. A row "has U+200B" at a commit if item `index` of its key contains U+200B.
2. If the row does not have U+200B at the census head, it is `not-at-head` and left out.
3. `git log --no-merges <head> -- <folder>/` lists the folder's commits, newest first (git's default order and history simplification). The introducing commit is the first listed commit C where the row has U+200B and C's first parent does not. If no listed commit qualifies (for example, the U+200B came in through a merge resolution), the row is `unattributed` and left out.
4. Kind: `folder-created` if the folder is absent in the parent (this includes the root commit, moves and first imports), `key-added` if the folder exists but the key or that item index does not, `edited` if the item existed without U+200B.
5. Weblate commit: the commit message matches `using Weblate` or `Translate-URL:` (case-insensitive; these are Weblate's default commit message and trailer, on Hosted Weblate and self-hosted instances), or the author or committer email ends in `@weblate.org`. Everything else is a non-Weblate commit.

## Predictions

Gate: at least 60 attributed rows from at least 15 repositories. Otherwise every prediction is NOT TESTABLE.

- **P1.** Fewer than half of the attributed rows were introduced by a Weblate commit (share < 0.5).
- **P2.** Among rows introduced by non-Weblate commits, at least half arrived with the string (`folder-created` or `key-added`) rather than as an edit of an existing translation (share >= 0.5).
- **P3.** P1's direction holds in every leave-one-repository-out subset: dropping any one repository leaves a Weblate share below 0.5.

Verdicts are computed by `grade()` in the code and will be copied into the results unchanged.

## What was seen before writing this

- The 90 rows themselves (keys, languages, the stored text) in `hits.csv`, which earlier census work produced. No commit history, blame or log of these repositories has been read.
- Background knowledge that informed the predictions: some of these apps are forks that merge translations from an upstream project with its own tooling (for example, SchildiChat Next from Element X, and moshidon and seqular from Mastodon's Android app), and one repository (Episteme) runs a self-hosted Weblate. This is why P1 predicts most U+200B came in outside Weblate.

## Reported but not predicted (exploratory)

Weblate share for pair-shaped rows versus other rows; per-repository counts; the `Translate-URL` hosts of Weblate commits (Hosted Weblate versus self-hosted); commit years; the kinds of Weblate-introduced rows; the subject line of each introducing commit (in `rows.csv`). No author names or emails are written out.

## Limits

- A Weblate commit that introduced U+200B does not by itself show an autofix gap: it can also come from a "replace" upload, an instance whose `AUTOFIX_LIST` leaves the fixup out, an older Weblate version, or a changed commit message template. The job cannot tell these apart from git alone.
- A project that rewrote Weblate's commit message without the `Translate-URL` trailer would be counted as non-Weblate.
- Squashed or rewritten histories push the introduction to the squash or import commit (counted as `folder-created` or `key-added`).
- The census's "weblate" platform label comes from repository markers, not from asking the projects how they translate.
- 90 rows in 23 apps is small, and a few apps hold many of the rows; P3 is there for that.

Made with AI agents. MV2, Munim, Inc., mv2@munimtech.com
