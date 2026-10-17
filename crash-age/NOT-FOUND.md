# Why crash_age could not find 5 of the 360 crash rows

MV2 of Munim, Inc. Made with AI agents; checked by reading the job's inputs and the strings.xml
files at the census commits on the web. Licence: CC BY 4.0.

[RESULTS.md](RESULTS.md) lists five crash rows whose census text `crash_age` 0.1.0 never found in
the file's history: four Wikimedia Commons `about_improve` rows (b+nds+NL, haw, hrx, hsb) and one
NewPipe row (in, `sign_in_confirm_not_bot_error`). The cause is a difference between two
versions of the rule that turns a strings.xml entry into the text the app gets. It is not a
missing commit, and it is not a problem with the census's findings.

## What the five rows have in common

They are the only rows in [callsites/findings.csv](../callsites/findings.csv) whose translation
holds a link written as escaped markup (`&lt;a href=\"...\"&gt;...&lt;/a&gt;`). No other crash
row has markup of any kind (`<a href=`, `<b>`, `<i>`, `<u>`, `<br`). Every other crash row was
found, apart from two in a repository that could not be cloned.

## The two rules

The text in findings.csv was made with the newer rule, the one l10n-guard 0.6.0 uses. It
removes only tags without attributes, so markup that is really text keeps any placeholder
inside it. The census's own `l10n_guard.py`, which `crash_age` downloaded (version 0.5.1 at
commit `2159ca6`, recorded in [crash_age.json](crash_age.json)), uses the older rule, which
removes every tag-like run. In the Upper Sorbian (hsb) Commons string, both links come out
differently:

| Rule | Text it gives (shortened) |
|---|---|
| newer (findings.csv) | `Žórłowy kod na <a href="https://github.com/commons-app/apps-android-commons">GitHub. ...` |
| older (crash_age 0.1.0) | `Žórłowy kod na GitHub. ...` |
| what the app gets | `Žórłowy kod na <a href="https://github.com/commons-app/apps-android-commons">GitHub</a>. ...` |

`crash_age` looks for an exact match, so it never found these five texts.

## Why this matters

- **These rows exist only because of the newer rule.** Their placeholder sits inside the link:
  `%2$s` in NewPipe's href, and `%20A` in the Commons Bugzilla URL, which `String.format` reads
  as a `%A` conversion with width 20. The older rule removes the whole opening tag, so it
  cannot see either one.
- **Neither rule is exactly right.** Escaped markup reaches the app as literal text, so `</a>`
  is part of the string. l10n-guard 0.6.0 still drops `</a>`, `<b>` and other tags without
  attributes when they are written as escaped text. This can't change a placeholder verdict,
  because the dropped runs cannot contain `%`, but it does change the text shown in reports.
  A fix is planned for l10n-guard after the 0.7.x releases.
- **The headline numbers barely move.** The five rows are 1.4% of the 360. Even if all five
  were older (or all younger) than every dated row, the median of the 353 dated rows would move
  at most three places in the sorted list.

## Not done

The five rows were not dated. A later `crash_age` would use the same text rule as findings.csv,
and the census repository's `l10n_guard.py` should be brought up to the rule its findings use.
