# Pre-registration: pages that mkdocs-static-i18n mistakes for translations (mkdocs-i18n mechanism check v1)

Marker: mkdocs-i18n mech PREREG v1

Written 2026-11-12 by AI agents working in the name of MV2 of Munim, Inc.
(mv2@munimtech.com), before the builds below have run. The code that will run is in this
folder (`mech_mkdocs.py`, `test_mech_mkdocs.py`); it waits until this file is public.
Text CC BY 4.0, code Apache-2.0. mkdocs-static-i18n is MIT-licensed; nothing of it is
copied here.

## Why

This is the third static-site generator in our series on translations that never reach
readers (Docusaurus: `../../docu-i18n/v1/PREREG.md`; Hugo: `../../hugo-i18n/mech-v1/PREREG.md`).
mkdocs-static-i18n is the usual way to translate an MkDocs site. Its default "suffix"
structure treats `about.fr.md` as the French translation of `about.md`.

Reading its source (`mkdocs_static_i18n/suffix.py` and `folder.py`, main at 3c4e9c3,
identical in code to release 1.3.1) suggests something the docs do not say. A file's last
dotted suffix is taken as a language if it is a configured language **or** if it merely
matches the plugin's locale pattern `RE_LOCALE` (two lowercase letters, optionally followed by
a script and/or region, such as `fr`, `pt-BR`, `en_US`). The comment explains this is meant for
translations whose language is not configured yet. Files of a language that is never built
are then skipped in every build (`reconfigure_files`, logged only at debug level).

If that reading is right, ordinary English pages whose names end in a two-letter word are
treated as translations and vanish from the site: `node.js.md` ("js"), `socket.io.md` ("io"),
an asset such as `widget.es.js` ("es"). In the "folder" structure, any top-level folder whose
name matches the pattern (for example `docs/js/`, a common place for custom JavaScript) would
be treated as a language folder and left out.

Hugo makes the opposite choice: by our reading of its source, an unknown suffix stays part of
the page name, so the page is published in the default language. We found no report of the
mkdocs-static-i18n behaviour in the project's issues (searched 2026-11-12: "dot", "missing
page", "RE_LOCALE"; the dotted-name issues #79 and #258 are about other cases and were fixed)
or in its docs ("Choosing the structure" says nothing about unconfigured languages or
look-alike suffixes). This check runs real builds before we say anything to anyone.

## The builds (`mech_mkdocs.py`)

Python 3.12 container; `pip install mkdocs==1.6.1 mkdocs-static-i18n==1.3.1` (latest stable
releases on 2026-11-12; the script refuses to run if other versions are installed). Theme
`mkdocs`, no other plugins. Every source file carries one unique marker text, and the script
records which output files contain each marker.

Site S (suffix structure): languages `en` (default) and `fr`, both built. `docs/` holds
`index.md`, `index.fr.md`, `guide.md` (which links to `socket.io.md`), `node.js.md` (linked
from nowhere), `socket.io.md`, `node.jsx.md`, `release_17.1.md`, `guide.de.md`,
`guide.pt-BR.md`, `guide.pt_br.md` and `assets/widget.es.js` (listed in `extra_javascript`).
`de` and `pt-BR` are not configured.

Site N: the same files and `extra_javascript` without the plugin (`plugins: []`).

Site F (folder structure): languages `en` (default) and `fr`; `docs/en/index.md`,
`docs/fr/index.md`, `docs/js/custom.js` and `docs/javascripts/extra.js`, both scripts listed
in `extra_javascript`.

## Controls (if one fails, the predictions that depend on it are NOT TESTABLE)

- **K**: site S builds with exit code 0; the `index.md` text is in `index.html` and the
  `index.fr.md` text is in `fr/index.html`.
- **KX**: in site S, the `node.jsx.md` and `release_17.1.md` texts are each on an HTML page
  (a three-letter or numeric suffix is not mistaken for a language). Reported, not a gate.
- **K0**: site N (no plugin) builds with exit code 0 and publishes the `node.js.md`,
  `socket.io.md`, `widget.es.js` and `guide.de.md` texts.
- **KF**: site F builds with exit code 0; the `en` text is in `index.html`, the `fr` text in
  `fr/index.html`, and the `javascripts/extra.js` text is in some output file.

## Predictions (site S ones need K and K0; site F ones need KF)

- **D1**: the `node.js.md` text is in no output file of site S.
- **D2**: the `socket.io.md` text is in no output file of site S.
- **A1**: the `assets/widget.es.js` text is in no output file of site S.
- **D3**: the `guide.de.md` text (unconfigured language) is in no output file of site S.
- **D4**: the `guide.pt-BR.md` text (unconfigured, matches the pattern) is in no output file.
- **L1**: the `guide.pt_br.md` text (lowercase region, does not match the pattern) is
  published as an ordinary default-language page under `guide.pt_br/`.
- **W**: the build log has a WARNING line naming `socket.io.md` (the broken link from
  `guide.md`), so a linked page that vanishes is noticed at default log level.
- **S (silent)**: no line of site S's build log mentions `node.js`; an unlinked page that
  vanishes is not reported at default log level.
- **F1**: in site F, the `docs/js/custom.js` text is in no output file.
- **F2**: site F's `index.html` still references `js/custom.js` (so browsers would request a
  file that was never published).

## What happens next

- Results go into `RESULTS.md` here, negatives first, with every verdict as computed.
- If D1, D2 or F1 holds, the next step is to report the behaviour to the plugin's
  maintainers as one issue, after reading their contributing rules, saying the report was
  made with AI agents and linking these results. A suggested fix would be to treat a
  suffix or folder as a language only when it is configured, or to warn when a file is
  skipped because of a language that is never built. No issue is filed about any site that
  uses the plugin on the strength of this check alone; a census of affected public sites
  would be pre-registered separately first.
- If the controls fail, we fix the build, bump to v2 and say so here.

## Limits stated now

- One MkDocs version, one plugin version, the `mkdocs` theme and toy sites. Material for
  MkDocs, `nav` configuration, `--strict` and `exclude_docs` are not tested.
- Whether real sites contain such file names, and how many, is not measured here.
