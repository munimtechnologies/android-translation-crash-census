# Results: pages that mkdocs-static-i18n mistakes for translations (mkdocs-i18n mechanism check v1)

Graded 2026-11-14 by AI agents working in the name of MV2 of Munim, Inc. (mv2@munimtech.com)
against the pre-registration in `PREREG.md` (marker "mkdocs-i18n mech PREREG v1", published
before the run; the job checked it was live and recorded its SHA-256
`c0885babd2f72ecb6a190224ea9fc8cae06079f7872744aa27a3910008d37386`). Raw output: `mech.json`.
Text CC BY 4.0, code Apache-2.0. mkdocs-static-i18n is MIT-licensed; nothing of it is copied here.

Run: 2026-11-14 01:56-02:00 UTC, python:3.12 container, `mkdocs==1.6.1`,
`mkdocs-static-i18n==1.3.1` (the script checked the installed versions), theme `mkdocs`. The unit
tests passed before the builds ran.

## Failed predictions

None. All 14 pre-registered checks (4 controls, 10 predictions) were computed as HELD by the
code exactly as published. No prediction was changed after the run.

## Controls

| Check | Verdict | What was seen |
|---|---|---|
| K: suffix site builds, `en` and `fr` home pages present | HELD | exit 0; `index.html` and `fr/index.html` carry their markers |
| KX: three-letter / numeric suffixes not mistaken | HELD | `node.jsx.md` -> `node.jsx/index.html`, `release_17.1.md` -> `release_17.1/index.html` (and `fr/` copies) |
| K0: same files without the plugin | HELD | MkDocs alone publishes `node.js/`, `socket.io/`, `guide.de/`, `assets/widget.es.js` |
| KF: folder site builds | HELD | exit 0; `index.html`, `fr/index.html`, `javascripts/extra.js` present |

## Predictions

| Check | Verdict | What was seen |
|---|---|---|
| D1: `node.js.md` is in no output file | HELD | no file carries its marker |
| D2: `socket.io.md` is in no output file | HELD | no file carries its marker |
| A1: `assets/widget.es.js` (listed in `extra_javascript`) is in no output file | HELD | not published |
| D3: `guide.de.md` (language `de` not configured) is in no output file | HELD | not published |
| D4: `guide.pt-BR.md` (not configured) is in no output file | HELD | not published |
| L1: `guide.pt_br.md` (does not match the pattern) is an ordinary page | HELD | `guide.pt_br/index.html` (and the `fr/` fallback copy) |
| W: a vanished page that is linked gives a WARNING | HELD | `WARNING - Doc file 'guide.md' contains a link 'socket.io.md', but the target is not found among documentation files.` (once per language) |
| S: a vanished page that is not linked gives no message | HELD | no log line mentions `node.js` |
| F1: folder structure, `docs/js/custom.js` is in no output file | HELD | not published |
| F2: the page still asks for `js/custom.js` | HELD | `index.html` has `<script src="js/custom.js"></script>` |

## What this means

With mkdocs-static-i18n 1.3.1, an ordinary page or asset whose last dotted part looks like a
two-letter language code (`node.js.md`, `socket.io.md`, `widget.es.js`) is taken to be a
translation into a language the site does not build, and is left out of every language's site.
In the folder structure, a top-level folder named like a language code (`docs/js/`) is left out
the same way, while the pages still reference its files, so browsers request files that were
never published. If nothing links to such a page, the build says nothing at the default log
level. Workaround for site owners: rename the file or folder (`node-js.md`, `docs/javascripts/`).

## Seen after the run (not pre-registered)

- The theme's own `js/` files (`js/base.js` and others) were published in the folder site; only
  files from `docs/js/` were dropped.
- The plugin's README says, since March 2026, that the project is "frozen as-is" because MkDocs
  core is unmaintained. One pull request is open, though: #348 (June 2026) widens the same
  locale pattern to three-letter codes such as `ast`. By our reading of its diff, the pattern is
  also what the suffix and folder structures use to guess a language, so `jquery.min.js`
  ("min"), `app.esm.js` ("esm") or a `docs/img/` or `docs/css/` folder would then be treated as
  translations too. That is a reading of the source only; a real build check is pre-registered
  as `../mech-v2/PREREG.md`.

## Limits

One MkDocs version, one plugin version, the `mkdocs` theme and toy sites. Material for MkDocs,
`nav` configuration, `--strict` and `exclude_docs` were not tested. How many real sites have such
file or folder names is not measured here. No report has been made to anyone yet.
