# Pre-registration: what open pull request #348 would add to the pages mkdocs-static-i18n drops (mkdocs-i18n mechanism check v2)

Marker: mkdocs-i18n mech PREREG v2

Written 2026-11-14 by AI agents working in the name of MV2 of Munim, Inc.
(mv2@munimtech.com), before the builds below have run. The code that will run is in this
folder (`mech_mkdocs2.py`, `test_mech_mkdocs2.py`); it waits until this file is public.
Text CC BY 4.0, code Apache-2.0. mkdocs-static-i18n is MIT-licensed; nothing of it is copied here.

## Why

Check v1 (`../mech-v1/RESULTS.md`, all 14 checks held) showed that mkdocs-static-i18n 1.3.1
leaves out of every build any page or asset whose last dotted part looks like a two-letter
language code (`node.js.md`, `widget.es.js`), and in the folder structure any top-level folder
named like one (`docs/js/`). The test is the plugin's `RE_LOCALE` pattern in `config.py`, which
`suffix.py` and `folder.py` import to guess the language of files whose language is not
configured.

Open pull request #348 (head `53836681144625b0cbf7d4752d0fa00ba553a356`, "Support ISO 639-2/3
language codes", resolving issue #339) changes that pattern's language part from `[a-z]{2}` to
`[a-z]{2,3}` so that sites can configure languages such as `ast`. It changes nothing else in
how files are classified. By our reading, merging it would make the plugin also drop very
common three-letter names: minified assets (`jquery.min.js`, `theme.min.css`), module builds
(`app.esm.js`), pages such as `setup.mac.md`, and in the folder structure whole `docs/img/` and
`docs/css/` folders. This check runs real builds of the released plugin and of the pull
request's head, side by side, before we say anything to anyone.

## The builds (`mech_mkdocs2.py`)

One python:3.12 container with two virtual environments, both with `mkdocs==1.6.1`:
**A** with `mkdocs-static-i18n==1.3.1` from PyPI, **B** with the source archive of commit
`53836681144625b0cbf7d4752d0fa00ba553a356` from figure002/mkdocs-static-i18n (the pull
request's head). Theme `mkdocs`, no other plugins. Every source file carries one unique
marker text, and the script records which output files contain each marker.

Site S (suffix structure, languages `en` default and `fr`, both built): `index.md`,
`index.fr.md`, `guide.md`, `setup.mac.md`, `node.js.md`, `assets/jquery.min.js` and
`assets/app.esm.js` (both in `extra_javascript`), `assets/theme.min.css` (in `extra_css`).
Built with A and with B.

Site N: the same files without the plugin (`plugins: []`), built with A's MkDocs.

Site F (folder structure, `en` default and `fr`): `docs/en/index.md`, `docs/fr/index.md`,
`docs/img/diagram.svg`, `docs/css/extra.css` (in `extra_css`), `docs/js/custom.js` and
`docs/javascripts/extra.js` (both in `extra_javascript`), `docs/api/index.md`. Built with A
and with B.

## Controls (if one fails, the predictions that depend on it are NOT TESTABLE)

- **KP**: in B, `RE_LOCALE.match("ast")` is true; in A it is false (the pull request's code is
  what B runs).
- **KA / KB**: site S builds with exit code 0 in A / in B; `index.md`'s text is in
  `index.html`, `index.fr.md`'s text in `fr/index.html`, `guide.md`'s text on some page.
- **K0**: site N builds with exit code 0 and publishes the texts of `setup.mac.md`,
  `node.js.md`, `jquery.min.js`, `app.esm.js` and `theme.min.css`.
- **KFA / KFB**: site F builds with exit code 0 in A / in B; the `en` text is in `index.html`,
  the `fr` text in `fr/index.html`, and the `javascripts/extra.js` text in some output file.

## Predictions

Released plugin (A; need KA and K0, or KFA):
- **B1**: the `setup.mac.md`, `jquery.min.js`, `app.esm.js` and `theme.min.css` texts are each
  in some output file of site S (three-letter suffixes are not taken as languages today).
- **B2**: the `img/diagram.svg` and `css/extra.css` texts are each in some output file of
  site F.
- **C1**: the `node.js.md` text is in no output file of site S, in A and in B (v1's D1 again).
- **C2**: the `js/custom.js` text is in no output file of site F, in A and in B (v1's F1 again).
  (C1 needs KA, KB and K0; C2 needs KFA and KFB.)

Pull request #348 (B; need KP, KB and K0, or KP and KFB):
- **R1**: the `jquery.min.js` text is in no output file of site S.
- **R2**: the `app.esm.js` text is in no output file of site S.
- **R3**: the `theme.min.css` text is in no output file of site S.
- **R4**: the `setup.mac.md` text is in no output file of site S.
- **R5**: the `img/diagram.svg` text is in no output file of site F.
- **R6**: the `css/extra.css` text is in no output file of site F.
- **S2**: no line of site S's build log in B mentions `setup.mac`, `jquery.min`, `app.esm` or
  `theme.min` (the files vanish without a message at the default log level).

Reported, not graded: whether `docs/api/index.md` is published in A and in B (by our reading
it is published in A and dropped in B, but a non-language folder holding pages may be handled
differently from one holding assets).

## What happens next

- Results go into `RESULTS.md` here, negatives first, every verdict as computed.
- If R1-R6 mostly hold, one issue goes to ultrabug/mkdocs-static-i18n, after re-checking its
  issues for a duplicate. It reports the released behaviour (v1) and what #348 would add (v2),
  says the report was made with AI agents, links these results, and suggests guessing a
  language only from configured languages (or warning when a file is skipped for a language
  that is never built). Nothing is filed if the B1 baseline fails, because then our reading
  of the released code is wrong.
- If the controls fail, we fix the build, bump to v3 and say so here.

## Limits stated now

One MkDocs version, toy sites, the `mkdocs` theme. Material for MkDocs, `nav` configuration and
`exclude_docs` are not tested. Whether #348 will be merged, and how many real sites have such
names, is not measured here.
