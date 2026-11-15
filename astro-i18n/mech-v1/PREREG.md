# PREREG: astro-mech-v1 (real Astro build of the astro-i18n checker's claims)

Written 2026-11-13, before any build. Filed as a job on 2026-11-15, still before any build.
Made with AI agents by MV2 of Munim, Inc. Text CC BY 4.0, code Apache-2.0.

Site (site/): astro 7.4.12, static output, defaultLocale 'en', prefixDefaultLocale false,
locales ['en', 'pt-BR', 'fr_CA', 'de', { path: 'spanish', codes: ['es'] }].
Folders: src/pages/pt-BR/ (locale spelling), src/pages/fr-ca/ (link spelling),
src/pages/spanish/, src/pages/blog/de.astro. Every page uses one layout that writes
<html lang={Astro.currentLocale}> and one <a data-code=...> per code with getRelativeLocaleUrl.
(Both pt-BR/ and pt-br/ can't exist in one working copy: the machine that prepares the job
has a case-insensitive file system.)

Job: image node:22 (has python3), `npm install astro@7.4.12`, `npx astro build`, then
`python3 check.py site /out`, which also runs the published checker astro_locales.py on site/.

Predictions (from astro_locales.py, source reading at withastro/astro 5b7c327):
- P1 dist/pt-BR/index.html has lang="pt-BR"; its pt-BR link is "/pt-br/"; dist/pt-br/ does not
  exist (case-sensitive Linux file system).
- P2 dist/fr-ca/index.html has lang="en" (default), not fr_CA; its fr_CA link is "/fr-ca/".
- P3 dist/spanish/index.html has lang="es"; its es link is "/spanish/".
- P4 dist/blog/de/index.html has lang="de" (later segment; intended per astro#9970).
- P5 astro_locales.py on site/ reports pt-BR folder links_case_only, fr-ca folder
  current_locale_wrong, blog/de.astro in later_segment_pages, findings == 2.
Verdict: the checker is "build-verified" only if P1, P2 and P5 all hold. Any miss is reported
first in RESULTS.md, and the README's claim is corrected before anything goes upstream.
Upstream (only if P1+P2 hold): read withastro/astro CONTRIBUTING + AI policy; maintainers asked
for "a bug report first" (#17984), so at most ONE issue (docs angle: the routing guide's
"match exactly" rule vs getRelativeLocaleUrl's default normalizing), never a PR first.

Deviation, 2026-11-15, before the build: the 2026-11-13 draft of site/astro.config.mjs could
not be copied into the job folder by the tools at hand, so it was rewritten from the
description above (same locales, defaultLocale and prefixDefaultLocale; `output` left at its
static default). No prediction was changed.
