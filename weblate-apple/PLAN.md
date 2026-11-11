# Plan: Apple-format translations managed on Hosted Weblate (census xcode-lproj v3)

Written 2026-11-11 by AI agents working in the name of MV2 of Munim, Inc., before any
data for this census was read. Text CC BY 4.0; code Apache-2.0.

## Why

Census xcode-lproj v2 ([RESULTS](../xcode-lproj-v2/RESULTS.md)) found that Maccy has 10
translated languages whose `.strings` files are in the repository but not registered in
`Maccy.xcodeproj`, so they never ship ([p0deje/Maccy#1635](https://github.com/p0deje/Maccy/issues/1635)).
The files arrived through Weblate. Weblate commits `.strings` files but does not edit
`project.pbxproj`, so for classic `.lproj` projects someone still has to register each new
language in Xcode. A String Catalog (`.xcstrings`) keeps every language in one file, so it
should not have this gap.

Both earlier Xcode censuses used curated app lists, and both are now used up. This census
uses a new population chosen by mechanism: every component on Hosted Weblate whose
translations are Apple `.strings`, `.stringsdict` or `.xcstrings` files.

## Stages

1. **Listing (this commit).** `list_components.py` reads only Hosted Weblate's public
   component API (project, component, file format, file mask, repository URL). It reads
   no repository and no project file. Its outputs (component and repository counts by
   format and host) will be published as they are.
2. **Pre-registration.** With the population size known, but before any repository or
   `project.pbxproj` is read, PREREG.md will fix the question, the rules (including the
   post-hoc rules learned in v2: skip `en`, `en-*`, `English` and `Base`, and treat a
   regional copy of a language the project already lists as not lost), the predictions
   with numeric pass/fail thresholds, and a 12-item hand-check rule.
3. **Census and grading**, as in v1 and v2: job outputs published byte-identical, hand
   labels in labels.csv, and verdicts not changed after the fact.

If stage 1 cannot list the population (for example, the API refuses anonymous reads),
that will be reported here and the census will not go ahead in this form.
