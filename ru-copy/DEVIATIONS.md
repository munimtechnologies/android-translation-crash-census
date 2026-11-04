# Deviations from the ru-copy pre-registration

ru-copy DEVIATION 1. Written 2026-11-04 by AI agents working for MV2 of Munim, Inc., before any
repository has been read. Nothing in [PREREG.md](PREREG.md) about the data, the predictions or
the grading changes.

## 1. One control case was wrong; the first job stopped at its own tests

**What happened.** The first job (`ru-copy-v1`, 3 November 2026, about 15:00 UTC) ran the unit
tests before anything else, and two failed. The job stopped there. It never reached the
pre-registration check, never downloaded the repository list and never read a repository. No
counts exist from it.

**Why.** PREREG.md lists the fixed cases the copy finder must get right before any data is read,
and one of them is wrong: "Настройки сохранены (copy, not flagged in Ukrainian ...)". The word
сохранены ends in ы, one of the four Russian-only letters of cyrillic-leak's Ukrainian rule. So
the published rule correctly flags it, and the control in `ru_copy.py` 0.1.0, which expected no
letter, failed. The scan test used the same string and failed the same way. The counting code
and the letter rule were right. The expectation was wrong.

**What changes (ru_copy.py 0.1.1).**

- The letter-free Russian copy in the control is now Удалить файл ("Delete file"). It has no ы,
  э, ё or ъ, so the Ukrainian letter rule can't see it, and the Belarusian rule flags its и.
  Настройки сохранены stays in the control with the answer the rule really gives (ы in
  Ukrainian, и in Belarusian).
- The tests use Удалить файл where they used Настройки сохранены, and check both strings' letters.
- The job now also waits for this file (mark `ru-copy DEVIATION 1`) to be public on `main` before
  it reads any repository, and records its SHA-256 next to PREREG.md's in `summary.json`. It
  records its own SHA-256 too.
- The version is 0.1.1. Nothing else in the code changes: same corpus, folders, units, pairs,
  copies, words, candidates, letter rule, thresholds, sample and grading.

**Why the results can't be affected.** The control only decides whether the job may start. It
is not used on the data. No data had been read when the change was made, so nothing seen could
have shaped it.

**One more correction to PREREG.md's background.** It says MultiVNC's Russian file held 17
Ukrainian strings, 12 of them with a Ukrainian-only letter. A re-check on 4 November found 22.
The other 5 are the encryption and encoding strings (зашифрований, незашифрований, Бажане
кодування, гаразд, Скасувати). This is background only and changes no prediction. MultiVNC's
maintainer merged the fix for all 22 on 4 November
([PR #321](https://github.com/bk138/multivnc/pull/321)).

## 2. The second job waited for this file and stopped (no change to the study)

The second job (`ru-copy-v2`, 4 November 2026, about 11:16 to 12:49 UTC) passed its tests and
found PREREG.md public. It then waited 90 minutes for this file, which had not been published
yet, and stopped as designed, before downloading the repository list or reading any repository.
The publishing step that should have put this file and `ru_copy.py` 0.1.1 on `main` was stopped
by an automatic content filter on an unrelated data file from another study in the same commit
(zh-vocab's `flagged.csv`, now left out).

The third job (`ru-copy-v3`) downloads `ru_copy.py` and `test_ru_copy.py` from `main` once 0.1.1
is public, so it runs the published files byte for byte, and records their SHA-256. Nothing in
the code, the data or the grading changes.
