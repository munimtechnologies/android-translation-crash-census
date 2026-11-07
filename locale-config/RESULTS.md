# Results: Android per-app language lists that don't match the app's translations

Graded on 2026-11-07 (UTC) by AI agents working for MV2 of Munim, Inc. The predictions in
[PREREG.md](PREREG.md) were published before any repository was read, and are graded here
unchanged. Code: [locale_config.py](locale_config.py) (Apache-2.0). Job outputs, published byte
for byte: [summary.json](summary.json), [lists.csv](lists.csv) (every hand-written list),
[sample.csv](sample.csv) (the C4 sample, label columns left empty by the job) and
[repos.jsonl](repos.jsonl). Hand labels: [labels.csv](labels.csv).

Job `locale-config-v1` ran on 2026-11-07 from 08:53 to 09:07 UTC. Its control and self-test passed,
and it recorded the pre-registration's SHA-256 (`96ea0819...8380e`) before reading any repository.
Of 4,693 repositories, 4,598 were read (95 could not be cloned), so the gate of 4,000 is met.
2,401 of them have Android translation folders.

## Verdicts: 4 of 4 held (C4 only just)

| | Prediction | Result | Verdict |
|---|---|---|---|
| C1 | at least 100 repositories with a hand-written list in the repository | 416 | HELD |
| C2 | at least a quarter of repositories with an evaluable list drift | 112 of 394 (28.4%) | HELD |
| C3 | more of them have an orphan than a phantom | 74 orphan vs 49 phantom | HELD |
| C4 | at least 3/4 of a 16-row sample is a real mismatch (hand check) | 12 of 16 | HELD |

**C4 is fragile.** 12 of 16 is exactly the threshold (12 x 4 = 48 = 16 x 3). One row is
borderline (summit: the missing languages are commented out of the list by hand, so leaving them
out may be deliberate). With that label flipped, 11 of 16 are real and C4 **fails**.

## What a mismatch means for users

Since Android 13 a user can pick a language for one app in the system settings. Settings offers
only the languages in the app's locale config. When a translation the app ships is missing from a
hand-written list (an **orphan**), Settings never offers it. When the list names a language the
app has no translation for (a **phantom**), Settings offers it and the user gets the default
language instead.

Confirmed examples from the hand check (each at the commit in [labels.csv](labels.csv)):

- **my-hackerspace** lists `dk` (Denmark's country code) instead of `da`, so its Danish
  translation is never offered and the list names a code that is not a language (how Settings
  shows `dk` was not checked).
- **autu-mandu** offers Ukrainian, but `values-uk/strings.xml` is an empty file; Chinese
  (`values-zh-rCN`) is translated but not listed.
- **prav** offers Hindi (`hi-IN`) from an empty file, and leaves out Estonian.
- **Vespucci** (osmeditor4android) offers Kannada and Occitan, which have no translated strings.
- **AppManager** (Dutch, Swedish), **BitBanana** (Swedish), **Urik** (Bulgarian), **Sky Map**
  (Galician), **PlainApp** (Turkish, Vietnamese), **MMRL** (Tamil) and **Flashy** (German, Spanish,
  Russian, Santali, Chinese) ship translations their lists leave out.

## Why 4 of the 16 were not real (method gaps, found by the hand check)

- **Build-time language filters (1 row, plus parts of 3 more).** CoMaps lists exactly the
  languages its `androidResources.localeFilters` keeps; its `eo`, `hr` and `lo` folders are left
  out of the app at build time, so they are not orphans. In MMRL, Flashy and Vespucci some reported
  languages failed for the same reason (or, in Vespucci, because presets are translated in `.po`
  files the method does not read), while at least one other language held. The method reads
  folders, not `localeFilters` or `resConfigs`.
- **Default language not English (2 rows).** Croustillapp's default strings are French and
  SrednaBG's are Bulgarian, with English in `values-en`. Without a `resources.properties`, the
  method assumed English, so the default language was counted as a phantom.
- **`@string` references (1 row).** SimpleTimeTracker writes all 29 entries as
  `@string/settings_..._tag`. The method read them as language names. It is the only list in
  [lists.csv](lists.csv) that does this.

So the 28.4% drift rate in C2, and the orphan count in C3, overstate the true rate by an amount we
did not measure precisely. With 12 of 16 sampled lists confirmed, a rough reading is that about
one in five evaluable lists (28.4% x 12/16 = 21%) has at least one real mismatch; this is a
post-hoc estimate from 16 rows, not a pre-registered number.

## Exploratory (not graded)

- **Most translated apps offer no per-app language choice at all.** Of 1,632 repositories with
  three or more translation languages, 1,036 have neither a hand-written list nor
  `generateLocaleConfig`, so Android 13+ Settings shows no language option for them (their in-app
  pickers, if any, are separate). Limits: a list added by another Gradle plugin, or written outside
  the files the job read, would be missed.
- 313 repositories generate their list with `generateLocaleConfig`. Three of them also have a
  folder named with a code that is not a language, which a generated list would offer: Exodus
  (`cn`), mako (`jp`) and Wikipedia (`qq`, the message-documentation pseudo-language). Whether each
  build really offers that code was not checked.
- 427 hand-written lists in 416 repositories: 423 parse, 4 point to a file that is not in the
  repository, and 23 are named in a build file (possibly rewritten at build time, not graded).
- The languages most often orphaned (by repository) are Turkish (15), Polish (14), Japanese (12),
  Chinese (11), Arabic and Estonian (10 each); the most frequent phantom is Hindi (9). Counts are
  before the hand check's corrections.

## Limits

- One commit per repository (HEAD on 2026-11-07); F-Droid apps only.
- The hand check was done by AI agents from the files at each recorded commit (GitHub and
  Codeberg APIs). It searched each repository's build files for language filters and references to
  the list, and the obvious script folders, but there is no code search across every file, so a
  script elsewhere that rewrites a list could have been missed.
- Languages only: region and script mismatches (`pt-BR` vs `values-pt-rPT`) are not counted.

## What happens next

- The pre-registration promised an l10n-guard check if C2 and C4 held. They did, C4 only at the
  threshold, so the check will be built with the three gaps above fixed (read `localeFilters` and
  `resConfigs`, detect a non-English default, skip `@string` entries) and tested on a fresh sample
  before release.
- The confirmed cases go on MV2's paced list of upstream reports (at most one outward action a
  day, only where a project's rules allow AI-assisted contributions, each saying it was made with
  AI agents).
