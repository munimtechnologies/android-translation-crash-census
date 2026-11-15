# Results: what Hugo does with translations whose language is not configured (mech-v1)

Pre-registration: [PREREG.md](PREREG.md) (marker "hugo-i18n mech PREREG v1"; the job checked
it was public and recorded its sha256 6fad54e4...30c0). Job `hugo-i18n-mech-v1`, run
2026-11-15 00:12 UTC with the official Hugo v0.169.0 linux-amd64 release (tarball sha256
2d2f0bfe...765a7, checked against the release checksums). The job's output is published
unchanged as `mech.json`. Made with AI agents by MV2 of Munim, Inc. Text CC BY 4.0, code
Apache-2.0.

## Correction, 2026-11-15 (added the same day, after publication)

The first version of this page said we "found no write-up of the single-file case (L1)". That
was wrong. A search of Hugo's tracker later the same day found Hugo issue
[#9343](https://github.com/gohugoio/hugo/issues/9343) (opened by Hugo's lead maintainer,
closed as completed for v0.121.0). It states the design directly: a page backed by
`foo.unknownlanguage.md` "will still be assigned the `defaultContentLanguage`". So L1 is
**intended behaviour**, recorded in the tracker since 2022, and not a bug.

What still stands, and what we now claim:

- The verdicts below are unchanged. They describe what v0.169.0 does, and they match #9343.
- Hugo's user documentation
  ([Multilingual mode](https://gohugo.io/content-management/multilingual/), read 2026-11-15)
  says what happens to files with *no* language code ("Hugo assigns it to the default
  language") but not what happens to a file whose code is not configured. The rule in #9343
  is in the tracker, not in the docs.
- The build printed no warning (check S). In the tracker searches we ran (issue search for
  "language not configured", "unknown language filename"), nobody asks Hugo to warn about
  this. Treat that as one search, not proof.
- The consequence a site owner sees: the foreign-language page is listed in the
  default-language section page and RSS feeds. #9343 implies this but does not spell it out.
- Page bundles behave differently (L3): the bundle's `index.de.md` is not published at all.
  #7256 (2020) reported the bundle case behaving the other way in an older Hugo.

So this is a measured, version-pinned description of a documented-in-the-tracker design, plus
a docs gap. It is not a new bug. We are not filing anything with Hugo on the strength of it.

## Limits and prior art (read first)

- One Hugo version, two toy sites. Themes, module mounts and the newer sites matrix were not
  tested. Nothing here says how many real sites are affected; that needs a separate census.
- Prior art: Hugo issues [#9343](https://github.com/gohugoio/hugo/issues/9343) (design of
  unknown language identifiers, see the correction above) and
  [#7256](https://github.com/gohugoio/hugo/issues/7256) (2020, page-bundle case). In v0.169.0
  the bundle case behaves differently from #7256 (L3 below: the German text is not published
  at all).
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

- **A translated file whose language is not configured is not dropped: it is published as a
  default-language (English) page**, as Hugo #9343 intends. `content/posts/hello.de.md` became
  `/posts/hello.de/` with `lang` `en`, and its German title was listed on the English section
  page (`posts/index.html`) and in the English RSS feeds (`index.xml`, `posts/index.xml`). The
  same happened to `hello.pt_br.md` (`/posts/hello.pt_br/`). Hugo printed no warning.
- In a page bundle the same file (`index.de.md`) is not published at all: it silently becomes
  a page resource.
- With content directories, a language folder that no language points to (`content/de`) is
  silently not built.
- A mixed-case suffix (`.pt-BR.md`) still works: Hugo lowercases it, so the docs sentence that
  the code "must be lowercase" is stricter than Hugo is. That is a docs nuance, not a bug.

So for Hugo there are three silent outcomes for the same mistake, depending on site layout:
published in the default language (single files, by design), dropped (bundles), or dropped
(content directories). Only the first is visible to readers, as a foreign-language page in
the default language's lists and feeds.

## Next

A census of real Hugo sites (how many publish an unconfigured-language file into the default
language) is drafted but not started. Because the behaviour is by design, its only use would
be to size the docs gap; it is low priority.
