# Three free format checks, three different blind spots

*By MV2 of Munim, Inc., made with AI agents. Part of the [Android translation-crash census](README.md). Text CC BY 4.0, code Apache-2.0.*

A project that takes in Android translations can run three open-source checks on them before they ship:

| check | where it runs | what it compares | severity |
|---|---|---|---|
| Weblate `java-printf-format` (JavaFormatCheck) | on Weblate, turned on by itself for Android string resources | placeholders found by its `JAVA_MATCH` pattern, source vs translation | warning unless the project enforces it |
| translate-toolkit `printf` test | `pofilter`, on files, in any CI | placeholders found by `printf_pat`, source vs translation | critical (fails the file) |
| Android Lint `StringFormatDetector` | `gradle lint`, on the resources | argument count and conversion class, default locale vs each translation | `StringFormatCount` warning, `StringFormatInvalid` / `StringFormatMatches` errors |

`checks_blind.py` runs all three over every translation the census found crashing in `java.util.Formatter` and records, per row, which of them would have said anything. The Weblate and translate-toolkit patterns are read from their own sources at pinned commits (`weblate_deps.py`, `checks_deps.py`; both are GPL and are never copied); Lint's pattern is Apache-2.0 and is copied, and `test_checks_blind.py` compares the copy with the downloaded Kotlin source. The comparison rules of each check are mirrored from the same sources (see the module docstring for what each does).

## What the reading says, verified on the census's hand-checked cases

Every row below is a real translation from `data/verified-cases.csv` (sources shortened to their placeholders), and every cell is asserted in `test_checks_blind.py` against the real patterns. The last row is synthetic.

| crashing translation (source) | mistake | Weblate | pofilter | Lint |
|---|---|---|---|---|
| Flashy fr/it/zh `… 25%.` / `25%。` (`… 25 percent`) | stray `%` added, placeholders intact | passes | passes | `StringFormatCount` |
| Flashy gl/pt/pt-BR `… 25% adicional…` (`… 25 percent`) | stray `%` added, read as `% a` | passes | passes | `StringFormatCount` + `StringFormatInvalid` |
| Cashiro `(%1$d%)` (`(%1$d%%)`) | escape dropped | passes | passes | `StringFormatCount` |
| Element X ja `%1$d% パーセント` (`%1$d percents`) | stray `%` added | passes | passes | `StringFormatCount` |
| Mastodon be `%,d% цытата` (`%,d quote`) | stray `%` added | passes | passes | `StringFormatCount` |
| Tallybook tr `Mesaj:% s` (`Message: %s`) | space inside placeholder | flagged | flagged | `StringFormatInvalid` |
| ownCloud ug `% 1 $ s / % 2 $ s` (`%1$s of %2$s`) | spaces inside placeholders | flagged | flagged | `StringFormatCount` |
| Commons ka `%1$ ატვირთულია` (`%1$s uploaded`) | conversion letter missing | flagged | flagged | `StringFormatCount` |
| FadCam el `%1$δδ` (`%1$ds`) | letter typed in Greek | flagged | flagged | `StringFormatCount` |
| Inure vi `%D vô hiệu hóa` (`%d disabled`) | wrong Latin letter | flagged | flagged | **ignored** |
| spaRSS ar plural `d% مقالات جديدة` (`%d new entries`) | placeholder mangled, in `<plurals>` | forgiven in some forms | flagged | **not visited** |
| *synthetic* tr `%25 ekstra` (`25%% extra`) | literal `%` before the number | passes | flagged | passes |

Three findings:

1. **Weblate and pofilter are blind to the same thing: a stray `%` that doesn't touch a real placeholder.** Both patterns only recognise a `%` that is followed by a conversion letter (Weblate: a Latin letter, and never after whitespace; translate-toolkit: any `\w` character, with no space flag). A `%` before a space, a period, `。`, `)` or the end of the string is not a placeholder to either, so when the real placeholders still match, the translation passes. That is the census's most widespread mistake (stray percent: 45 reachable rows in 26 apps). Formatter, on the other hand, throws at exactly that `%`: `UnknownFormatConversionException` before punctuation, and before a space and a word starting with a conversion letter (`25% adicional`) it reads `% a` as one more placeholder and throws `MissingFormatArgumentException`.
2. **Lint sees the stray `%`, but its message depends on the next word, and it has its own blind spots.** A `%` with no valid placeholder after it makes Lint classify the whole translation as "not a format string"; the comparison then counts it as zero arguments and reports `StringFormatCount` ("inconsistent number of arguments"), a warning with a misleading message, and nothing at all when the default string has zero arguments itself (the synthetic row). Lint's own pattern, like Formatter's, accepts a space as a flag, so when the next word starts with a conversion letter (Flashy's Galician and Portuguese `25% adicional`) the stray `%` becomes a second argument: `StringFormatCount` plus a `StringFormatInvalid` error ("missing conversion character in '% a'?"), the one stray-percent case where Lint raises an error. A translation whose `%` is followed by a Latin letter Lint doesn't know (`%D`, `%i`, `%u`) is *ignored* entirely, never compared. And `StringFormatDetector` visits `<string>` elements only, never `<plurals>` items, so every plural row in the census is outside its reach.
3. **translate-toolkit's `\w` is both its strength and its weakness.** `%1$с`, `%1$δδ`, `%D` and `%25` are all "placeholders" to it, so they are flagged as different from the source (for the right reason or by accident), while a `%` before whitespace or punctuation is invisible, like in Weblate.

No single check sees all of the hand-verified cases. The union of the three sees all but the synthetic row, and only pofilter sees that one.

## Counts over the whole census

Compute job `checks-blind-v2` (2026-10-15, 29 of 29 tests passed) ran `checks_blind.py` over the published `data/findings.csv`. Before counting it drops date conversions (`%t`, which need a date argument the census doesn't model), 5 rows that print wrong text instead of crashing, and 11 rows from a repository that has since been cleared. That leaves **366 crashing translations in 98 repositories**; 237 of them, in 66 repositories, are strings the app's code is seen to format ("formatted"). Full tables: [`data/checks-blind.md`](data/checks-blind.md); one row per translation: [`data/checks-blind-rows.csv`](data/checks-blind-rows.csv).

| | Weblate | pofilter | Lint |
|---|---|---|---|
| flagged (all 366) | 300 | 322 | 239 |
| not flagged | 27 | 44 | 2 |
| depends on the plural form / not visited / ignored | 39 plural-dependent | - | 90 not visited (plurals), 35 ignored |
| flagged (237 formatted) | 198 | 215 | 176 |

Which checks see each crashing translation:

| seen by | all rows | repos | formatted rows | repos |
|---|---:|---:|---:|---:|
| Weblate + pofilter + Lint | 212 | 57 | 164 | 41 |
| Weblate + pofilter | 68 | 30 | 32 | 16 |
| pofilter only | 41 | 21 | 18 | 13 |
| Weblate + Lint | 14 | 1 | 0 | 0 |
| Weblate only | 6 | 3 | 2 | 2 |
| pofilter + Lint | 1 | 1 | 1 | 1 |
| **Lint only** | **12** | **4** | **11** | **3** |
| **none of the three** | **12** | **9** | **9** | **7** |

So **24 crashing translations pass both Weblate and pofilter**, and **12 of them pass all three checks**. 22 of the 24 are the same mistake: an extra lone `%` in a translation that keeps every real placeholder of the source, followed by a space, punctuation, a non-Latin letter or the end of the string. The other 2 (Material Files eu) rewrite `%1$,d` as `%1$` plus a word starting with `e`, which Formatter reads as a space flag and an `e` conversion given an Integer. pofilter can't parse the source's comma flag (its flag class is `[+#-]*`), so it sees no placeholder on either side.

The 12 that no check sees, and why each misses:

| app | locale | what follows the stray `%` | why Lint misses it |
|---|---|---|---|
| Exodus | tr, 2 plural forms | ` (` (read as two flags, then a `%` conversion) | plurals not visited |
| Element X | ja, plural | ` パ` | plurals not visited |
| SchildiChat Next | ja, plural | same row, a git-merge fork copy of Element X | plurals not visited |
| Mastodon | be-rBY, plural | ` ц` | plurals not visited |
| Moshidon | be-rBY, plural | same row, a git-merge fork copy of Mastodon | plurals not visited |
| Homer | zh-rCN, 2 plural forms | end of the string | plurals not visited |
| LibreTorrent | cs, string | ` ú` | its pattern needs an ASCII conversion letter |
| Commons | sl, string (not referenced in code) | a no-break space (`&nbsp;`) | same: a non-ASCII character after `%` |
| Material Files | eu, 2 plural forms | `%1$` + ` e…` (see above) | plurals not visited |

10 of the 12 are in `<plurals>`, where Lint never looks; the other 2 have a non-ASCII character right after the `%`. The 12 that only Lint sees are all `<string>` elements: Flashy (6 languages), Cashiro (3), PIA VPN (2) and Petals (1).

By mistake kind ([taxonomy](data/taxonomy.md)), the stray percent is the weakest spot: of its 82 rows Weblate flags 53, pofilter 55 and Lint 41, and 8 are seen by none. The other 4 unseen rows are filed under flag mismatch (Exodus, where the stray `%` before ` (` parses as flags) and wrong type (Material Files). Every malformed index, missing or native-script conversion letter, invalid conversion and argument the app doesn't pass is seen by at least one check.

## A rule that would catch the 22

> If the source string has at least one format placeholder, flag every `%` in the translation that is neither `%%` nor the start of a placeholder the check recognises.

Limiting the rule to strings whose source has a placeholder avoids the false positive the checkers presumably avoid on purpose: French `50 % de remise` in a string that is never formatted. A string with a placeholder is passed to `String.format`, where every `%` must be part of a specifier, so in those strings a lone `%` is never harmless. Two smaller fixes would close the rest: translate-toolkit's flag class could take all of Java's flags (`-#+ 0,(<`), and Lint's `StringFormatDetector` could visit `<plurals>` items. `l10n_guard.py` in this repository parses translations with Java's own grammar instead of a placeholder pattern, so to it, as to Formatter, a stray `%` is either a parse error or one argument too many.

This is a proposal; it has not been filed with Weblate, translate-toolkit or Android Lint yet.

## Limits

- By reading the checks' sources at pinned commits (Weblate `9757411`, translate-toolkit `8298558`, Lint `mirror-goog-studio-main` as of 2026-10-15), then testing the mirrored rules on real rows. The checks themselves were not run inside Weblate, pofilter or Gradle.
- Default configurations only. A Weblate project can enforce the check or add flags; a Lint run can raise `StringFormatCount` to an error or suppress it.
- The checks run on the census's extracted text, not the raw XML, so `formatted="false"`, `tools:ignore` and escaping differences are not modelled.
- Weblate's plural leniency is approximated (both strict and lenient results are kept); translate-toolkit's `%.0s` leniency is mirrored.
- The counts are over the published census data (`data/findings.csv`), not over a later rerun; they will move a little when the data is regenerated. "Seen by" means a check reports something about the string, not that its message names the real problem (see finding 2).
- Crowdin, Transifex, Lokalise and Localazy have closed-source checks; nothing here says anything about them.

## Corrections

- 2026-10-15: a first draft of this page (never published) listed Flashy's six languages in one row with `StringFormatCount` only. Re-reading Lint's source against the draft's test, before anything was published, caught the mistake: in gl, pt and pt-BR the stray `%` is followed by `adicional`, which Lint reads as `% a`, so Lint also raises `StringFormatInvalid`. The row is now split in two.

## Prior art

Weblate issue #4623 (auto-enabling the Java check for Android), Android Lint's `StringFormatDetectorTest`, and the per-project fixes listed in the README. No comparison of what these checks miss on real shipped translations was found, and no report naming the shared stray-`%` / plurals gap across the three checks (searches 2026-10-15 and 2026-10-16).
