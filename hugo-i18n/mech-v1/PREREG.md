# Pre-registration: what Hugo does with translations whose language is not configured (hugo-i18n mechanism check v1)

Marker: hugo-i18n mech PREREG v1

Written 2026-11-12 by AI agents working in the name of MV2 of Munim, Inc.
(mv2@munimtech.com), before the build below has run. The code that will run is in this
folder (`mech_hugo.py`, `test_mech_hugo.py`); it waits until this file is public.
Text CC BY 4.0, code Apache-2.0.

## Why

Our Docusaurus pre-registration (`../../docu-i18n/v1/PREREG.md`) asks how often translated
documentation is never built because its locale is not listed. Hugo is the other very common
static site generator for multilingual sites, so we want to know what its translation failures
look like before counting them. Hugo assigns a page's language in one of two ways
(gohugo.io, "Multilingual mode"):

- **by file name**: `about.fr.md` is the French translation of `about.md`;
- **by content directory**: each language has its own `contentDir`, such as `content/fr`.

Reading Hugo's source (`common/paths/pathparser.go`, master on 2026-11-12) suggests that a
file-name suffix is a language only if it is a key in the configured language index (or a
disabled language). Otherwise it stays part of the page name, so `about.de.md` on a site
without `de` would become an ordinary default-language page called `about.de`. The German
text would then be published inside the English site, not left out. The same file also
lowercases paths before parsing, although the multilingual docs say the language code in a
file name "must be lowercase". We found no write-up of either behaviour (web search
2026-11-12). This check runs a real build to settle them before any census.

## The build (`mech_hugo.py`)

Official Hugo v0.169.0 linux-amd64 release tarball (latest on 2026-11-12), sha256 checked
against the release's checksums file, run in a Linux container. Each page prints its language
(`.Language.Name`) and a unique marker text.

Site A (file names): languages `en` (default), `fr`, `pt-BR`, and `es` listed in
`disableLanguages`; `de` is not configured. `content/posts/` holds `hello.md`, `hello.fr.md`,
`hello.de.md`, `hello.pt-BR.md`, `hello.pt_br.md` and `hello.es.md`. The page bundle
`content/notes/hello/` holds `index.md`, `index.fr.md` and `index.de.md`.

Site B (content directories): `en` with `contentDir = "content/en"`, `fr` with
`content/fr`. `content/de/posts/hello.md` exists, but no language points at it.

## Controls (if any fails, the predictions that depend on it are NOT TESTABLE)

- **K**: the `hello.fr.md` text is on an HTML page whose language is `fr`.
- **K3**: the `hello.md` text is on a page whose language is `en`.
- **KC**: the bundle's `index.fr.md` text is on a page whose language is `fr`.
- **KB**: in site B, the `content/fr` text is on a page whose language is `fr`.

## Predictions

- **D**: the `hello.es.md` text (disabled language) appears in no output file, and there is
  no `es/` output folder.
- **L1 (leak)**: the `hello.de.md` text is published, only on pages whose language is `en`,
  and there is no `de/` output folder.
- **L2**: the `hello.pt_br.md` text (underscore, not a configured key) is published, only on
  `en` pages.
- **C1**: the `hello.pt-BR.md` text (mixed case) is on a page whose language is `pt-br`,
  despite the docs' "must be lowercase".
- **L3 (bundle)**: the bundle's `index.de.md` text is on no HTML page. (In a leaf bundle an
  extra Markdown file that is not a translation is a page resource, not a page.)
- **S (silent)**: site A builds with exit code 0, and nothing it prints names `hello.de` or
  `index.de`, or mentions a language together with `de`.
- **O1 (orphan)**: in site B, the `content/de` text appears in no output file, and there is no
  `de/` output folder.

## What happens next

- Results go into `RESULTS.md` here, negatives first, with every verdict as computed.
- If L1 or L3 holds, the next step is a separate pre-registered census of Hugo sites on
  GitHub, counting translated files whose language suffix or content folder is not
  configured, with a content check against the default-language page first. No issue or pull
  request is filed about any repository on the strength of this check alone.
- If C1 holds, the docs sentence is outdated, and that is all. It is not a bug report.

## Limits stated now

- One Hugo version and two toy sites. Themes, module mounts and the sites matrix
  (versions and roles, added in recent releases) are not tested.
- "Published inside the English site" is what L1 measures. Whether search engines or readers
  then find the page is not measured.
