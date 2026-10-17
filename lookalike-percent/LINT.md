# lookalike-percent: what Android Lint says about `٪s` and `％d`

MV2 of Munim, Inc., made with AI agents, 2026-10-17. Text CC BY 4.0.
Answers the open question in [FINDINGS.md](FINDINGS.md) ("Not tested: what
Android Lint reports for these strings"). We **read** Lint's source; we did not
run Lint on these apps.

Source read: `StringFormatDetector.kt` in AOSP `platform/tools/base`, branch
`mirror-goog-studio-main`, blob `d9d20692b334fd2c524aba1377661eedd3ed7f69`
(Apache-2.0), read 2026-10-17. Older Android Gradle Plugin versions may differ.

## Short answer

Lint catches some of these strings, under a generic message, and only when
someone runs the full `lint` task. It never names the look-alike character. It
is blind to the plural strings and to translations that mix a look-alike with an
ASCII placeholder, and the check that runs during release builds skips it.

## How the detector decides

- It treats a string as a format string only if it contains the ASCII `%`
  (U+0025) followed by a valid conversion (`FORMAT` regex `%(\d+\$)?...[a-zA-Z%]`).
  `٪` (U+066A) and `％` (U+FF05) are ordinary characters to it.
- It visits `<string>` elements only (`getApplicableElements` returns
  `TAG_STRING`). `<plurals>` items are never checked, and checking
  `getQuantityString` calls is still a TODO in the source.
- At call sites it checks `format`, `getString` and Compose `stringResource`
  (two-argument form), and only when it can resolve the string resource.

## What that means for each kind of look-alike

| Kind of translation | Lint result | Cases from FINDINGS.md |
|---|---|---|
| `<plurals>` item with `％d` / `٪d` | Nothing. The detector doesn't look at plurals. | Threema zh-rCN `really_delete_thread_message`, TrackerControl ja-rJP `n_companies_found` |
| `<string>` with a look-alike and **no** ASCII `%` | The translation is classed "not formatted". In the XML pass: **StringFormatCount** (warning), "Inconsistent number of arguments in formatting string `x`; found both 0 here and 1 in values/strings.xml". At a call site Lint can resolve that passes arguments: **StringFormatInvalid** (error), "Format string '`x`' is not a valid format string so it should not be passed to `String.format`", with the translation as secondary location ("This definition does not require arguments"). | Windscribe ar/fa (`stringResource(R.string.set_this_protocol_as_preferred, ...)`, `getString(R.string.ping_time, pingTime)`), APK Explorer & Editor ar-rSA (`getString(R.string.android_version, ...)` and others): expected to get both, if their whole translation has no ASCII `%` |
| Same, but the call passes the id in a variable, or nests `getString` inside `String.format` | XML warning only, unless Lint's `ResourceEvaluator` can trace the resource (not settled by this reading) | SimpleStorage ja (`getString(resId, rootPath)`, `resId` is a parameter); Retro Music zh-rCN (`String.format(getString(R.string.delete_song_x), title)`) |
| Look-alike **plus** an ASCII placeholder, same count as the source | Nothing. The string is "formatted", the counts agree, and the look-alike is plain text to Lint. | EventFahrplan ja `schedule_parsing_error_with_version` (`％s` ... `%s`) |

## Why these still ship

- StringFormatCount is a Warning and StringFormatInvalid an Error, not Fatal.
  `lintVitalRelease`, the Lint pass that runs during release builds by default,
  checks only Fatal issues (AGP `checkReleaseBuilds`). A release build passes
  unless the project runs the full `lint` task in CI or raises these issues to
  `fatal`.
- When the error does fire, it reads as if the *code* is wrong ("should not be
  passed to `String.format`"). The real cause, a `٪` or `％` that looks like the
  ASCII sign, is only visible by opening the translation and knowing to look.

## What this changes

- A look-alike check is still needed for plurals and mixed strings, where
  neither Lint nor a generic "placeholder missing" check says why. The next
  version of [l10n-guard](https://github.com/munimtechnologies/l10n-guard) is
  planned to name the character when a placeholder is missing and `٪` or `％`
  sits where it should be.
- Limits: source reading only; we did not confirm which Lint version each app
  uses, whether it runs Lint, or that each whole translation lacks an ASCII `%`
  (the table says "expected" for that reason).
