# census_callsites 0.1.0 predictions: can simple call-site rules find the crashes the census missed?

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-17, before census_callsites.py was first run.
Licence: this text CC BY 4.0; census_callsites.py, fetch_code.py and the tests Apache-2.0.

## Question

Census 0.4.0 counts a crashing translation as reachable ("formatted") only when its string is named in a
getString / stringResource / getQuantityString / pluralStringResource call with format arguments, or a
no-argument getString / stringResource call is wrapped in String.format or .format(). It found 360
crashing translations: 232 formatted, 40 only "referenced" and 88 never named in the code.

The [hand audit of those 40](../data/referenced-crash-audit.md) found 34 that throw (25 crashes, 8 caught,
1 with an unconfirmed trigger) and 6 that don't. They were missed because the id is stored and formatted
later (`val id = if (...) R.string.a else R.string.b; getString(id, name)`), passed to a helper with its
arguments (`Builder.content(id, args)`, `logInfo(id, name)`), fetched first and formatted later, or
wrapped in String.format behind a receiver chain (`String.format(getResources().getString(id), x)`).

census_callsites 0.1.0 turns those findings into four rules (`wrapped`, `fetched`, `helper`, `stored`;
see the docstring of [census_callsites.py](census_callsites.py)) and labels a matching "referenced"
string as a "candidate": a call site worth reading, not a confirmed crash. Census 0.4.0's verdicts and
its "formatted" label are unchanged.

Android Lint's StringFormatDetector also matches literal `R.string.x` references at call sites. A brief
search found no measurement of how many translation crashes such literal-reference matching misses, or
of rules that recover them; this is a short prior-art check, not a complete one.

## What we had already seen

The 40 audited rows and their call sites (we wrote the rules from them, so C1 is partly an in-sample
check: it tests whether the rules, as coded, actually match code we only described in prose). We have
not run the rules on any repository, and have not counted "referenced" strings outside the 40 crash
rows.

## Method (fixed now)

- Data: the same F-Droid repositories and strings as census 0.4.0 (census.py 0.3.0 + census_fixes 0.3.1
  + census_plurals 0.4.0, fetched from this repository at run time), at each repository's current
  default branch. Audited rows that are no longer crashes (fixed upstream since) are left out of C1/C2.
- An audited row matches a finding by repository, locale and key.
- A prediction whose rows are all missing is "not testable".
- The job refuses to run until this file is on main.

## Predictions

- C1. At least 80% of the hand-audited rows that throw (and still crash) are "formatted" or "candidate".
- C2. The two hand-audited rows that are not formatted (Wikimedia Commons nqo
  add_picture_to_wikipedia_article_desc; Your local weather ar title_activity_license) stay "referenced".
- C3. The rules are selective: at most half of the strings census 0.4.0 calls "referenced" (over all
  flagged translations, not only crashes) become candidates.

## Limits

- The rules read text, not types: a helper or a stored id may never reach a format call, and a
  prefs/bundle `getString(key, default)` may be taken for a resource lookup (the `stored` rule only needs
  one such call in the repository). "candidate" means "read this call site", nothing more.
- The rules were written from the 40 audited rows, so C1 measures fit, not discovery; C3 and the
  candidates outside the audit are the out-of-sample part.
- Only .kt and .java files are read; ids looked up by name at runtime (getIdentifier) are still missed.
