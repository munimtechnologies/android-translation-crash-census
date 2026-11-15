# Results: what Hugo does with translations whose language is not configured (mech-v1)

Pre-registration: [PREREG.md](PREREG.md) (marker "hugo-i18n mech PREREG v1"; the job checked
it was public and recorded its sha256 6fad54e4...30c0). Job `hugo-i18n-mech-v1`, run
2026-11-15 00:12 UTC with the official Hugo v0.169.0 linux-amd64 release (tarball sha256
2d2f0bfe...765a7, checked against the release checksums). The job's output is published
unchanged as `mech.json`. Made with AI agents by MV2 of Munim, Inc. Text CC BY 4.0, code
Apache-2.0.

## Limits and prior art (read first)

- One Hugo version, two toy sites. Themes, module mounts and the newer sites matrix were not
  tested. Nothing here says how many real sites are affected; that needs a separate census.
- Part of this is already known. Hugo issue
  [#7256](https://github.com/gohugoio/hugo/issues/7256) (2020) reported that in a page bundle,
  `index.de.md` without a configured `de` is treated as a default-language file. In v0.169.0 the
  bundle case behaves differently (L3 below: the German text is not published at all). We
  found no write-up of the single-file case (L1), where the German page *is* published inside
  the English site; one web search on 2026-11-15, so absence is not proof.
- No issue or pull request is filed about any project on the strength of this check.

## Verdicts (all 11 held, as the job wrote them)

| Check | What was predicted | Verdict |
|---|---|---|
| K, K3, KC, KB (controls) | configured languages land on pages of that language | HELD |
| D | `hello.es.md` (language in `disableLanguages`) is published nowhere | HELD |
| **L1 (leak)** | `hello.de.md` with no `de` configured is published, only on `en` pages, no `de/` folder | HELD |
| L2 | `hello.pt_br.md` (underscore, not a configured key) is published only on `en` pages | HELD |
| C1 | `hello.pt-BR.md` (mixed case) lands on the `pt-br` page, despite the docs' "must be lowercase" | HELD |
| L3 (bundle) | the bundle's `index.de.md` text is on no HTML page | HELD |
| S (silent) | site A builds with exit 0 and prints nothing about `hello.de` / `index.de` | HELD |
| O1 (orphan) | site B's `content/de` folder, not pointed to by any language, is published nowhere | HELD |

## What the build shows

- **A translated file whose language is not configured is not dropped: it is published as an
  English page.** `content/posts/hello.de.md` became `/posts/hello.de/` with `lang` `en`, and
  its German title was listed on the English section page (`posts/index.html`) and in the
  English RSS feeds (`index.xml`, `posts/index.xml`). The same happened to `hello.pt_br.md`
  (`/posts/hello.pt_br/`). Hugo printed no warning.
- In a page bundle the same file (`index.de.md`) is not published at all: it silently becomes
  a page resource.
- With content directories, a language folder that no language points to (`content/de`) is
  silently not built.
- A mixed-case suffix (`.pt-BR.md`) still works: Hugo lowercases it, so the docs sentence that
  the code "must be lowercase" is stricter than Hugo is. That is a docs nuance, not a bug.

So for Hugo there are three silent outcomes for the same mistake, depending on site layout:
leaked into the default language (single files), dropped (bundles), or dropped (content
directories). Only the first is visible to readers, as a foreign-language page in the default
language's lists and feeds.

## Next

A separate pre-registered census of Hugo sites on GitHub (translated files whose suffix or
content folder is not configured, with a content check against the default-language page)
may follow. It is not started yet.
