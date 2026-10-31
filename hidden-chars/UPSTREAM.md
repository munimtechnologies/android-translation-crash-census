# Upstream reports from the hidden-chars census

Reports MV2 of Munim, Inc. filed to app projects about stray invisible characters this census found, and what happened to each. Every report was re-checked against the project's current files before filing, says it was made with AI agents, and was filed one at a time.

| Project | Report | Filed | What it covered | Outcome |
|---|---|---|---|---|
| Nightdream (firebirdberlin/nightdream) | [#389](https://github.com/firebirdberlin/nightdream/issues/389) | 2026-10-30 | 13 strings in 10 languages with U+200B, 12 of them the "space + two U+200B" shape, 9 right after "EXIF" | **Fixed the same day** by the maintainer in [2b262b2](https://github.com/firebirdberlin/nightdream/commit/2b262b2f96bdbbe8d2f00075b3568ac68083cd2d) ("Removed all occurrences of U+200B from the translated string values", closes #389): 14 lines in 11 files |

Note on the Nightdream fix: it also removed the same "EXIF + space + two U+200B" shape from `values-th/strings.xml`. The report had left Thai out on purpose, because Thai text can use U+200B as a word-break hint and the census skips th, lo, my, km, bo and dz. That this Thai string had the same shape after the same word as the other ten languages suggests the census's language filter hides some of this artifact in those languages. This is one string, so it is a note, not a finding.

Made with AI agents. MV2, Munim, Inc., mv2@munimtech.com
