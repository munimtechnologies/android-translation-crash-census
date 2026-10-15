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

Pending: `checks_blind.py` over `data/findings.csv` (compute job `checks-blind-v2`) will add, per mistake kind, how many of the 371 crashing translations (238 reachable) each check flags and how many none of them sees. Until then the table above is the evidence: it is the hand-verified subset, not a sample.

## Limits

- By reading the checks' sources at pinned commits (Weblate `9757411`, translate-toolkit `8298558`, Lint `mirror-goog-studio-main` as of 2026-10-15), then testing the mirrored rules on real rows. The checks themselves were not run inside Weblate, pofilter or Gradle.
- Default configurations only. A Weblate project can enforce the check or add flags; a Lint run can raise `StringFormatCount` to an error or suppress it.
- The checks run on the census's extracted text, not the raw XML, so `formatted="false"`, `tools:ignore` and escaping differences are not modelled.
- Weblate's plural leniency is approximated (both strict and lenient results are kept); translate-toolkit's `%.0s` leniency is mirrored.
- Crowdin, Transifex, Lokalise and Localazy have closed-source checks; nothing here says anything about them.

## Corrections

- 2026-10-15: a first draft of this page (never published) listed Flashy's six languages in one row with `StringFormatCount` only. Re-reading Lint's source against the draft's test, before anything was published, caught the mistake: in gl, pt and pt-BR the stray `%` is followed by `adicional`, which Lint reads as `% a`, so Lint also raises `StringFormatInvalid`. The row is now split in two.

## Prior art

Weblate issue #4623 (auto-enabling the Java check for Android), Android Lint's `StringFormatDetectorTest`, and the per-project fixes listed in the README. No comparison of what these checks miss on real shipped translations was found (searches 2026-10-15).
