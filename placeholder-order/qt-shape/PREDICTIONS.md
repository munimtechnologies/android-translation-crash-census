# qt-shape 0.1.0 predictions: does genitive order decide which "X of Y" strings translators reorder?

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-17, before qt_shape.py was first run.
Licence: this text CC BY 4.0; qt_shape.py, fetch_code.py and the tests Apache-2.0.

## Question

[shape 0.1.0](../shape/RESULTS.md) found, in Android apps on F-Droid, that translators into verb-final
(SOV) languages reorder "%1$d of %2$d" strings 53.2% of the time and strings joined only by punctuation
0.9% of the time. All six of its predictions held.

Reading its per-language table afterwards, we saw something we had not predicted. The "of" reorders
seem to follow a language's genitive order (WALS feature 86A), not its clause order (81A):

| F-Droid, "of" sources | Genitive-Noun (86A) | Noun-Genitive (86A) |
|---|---|---|
| SOV | 1,191 of 2,090 reordered (57.0%), 18 languages | Persian only: 1 of 192 (0.5%) |
| not SOV | 217 of 2,047 (10.6%), 8 languages; 57 of 1,282 (4.4%) without Chinese | 4 of 5,873 (0.07%), 24 languages |

(Groups as in placeholder-order 0.1.0, genitive order from np-order's WALS table; only the 75
languages in that table are pooled.)

Persian is SOV but puts the genitive after the noun, and almost never reorders "of" strings. Chinese is
SVO but puts the genitive first, and reorders them 20.9% of the time (160 of 765). Hungarian, Estonian,
Latvian and Lithuanian (genitive first) reorder them 3-15% of the time. French, Spanish, Italian,
Portuguese, German and Russian, all Noun-Genitive, reorder them at 0.0-0.6%.

[np-order 0.1.0](../np-order/RESULTS.md) could not separate the two features, because it compared
whole languages, where they mostly go together. A source's shape lets the test look at the strings
where genitive order should matter. But this reading was made after looking at the data, with a single
SOV Noun-Genitive language, so it needs data it was not drawn from.

The test here uses the Qt Linguist `.ts` files that 39 open-source Qt projects keep in their
repositories (qBittorrent, KeePassXC, Nextcloud desktop, MuseScore, Bitcoin Core, FreeCAD and others;
the list is `REPOS` in [qt_shape.py](qt_shape.py)). In Qt, `%1` and `%2` are numbered, so translators
can put them in any order. These are desktop Qt code bases, not the Android repositories shape 0.1.0
read, although some translators may work on both.

Prior art: a brief search (2026-10-17) found style guides and single examples (a Galician WordPress
string, a cmux pull request about Japanese "Move %@ to %@"), but no measurement of which languages
reorder "X of Y" strings or of any link to genitive order.

## What we had already seen

The F-Droid numbers above, from shape 0.1.0's by_language.csv joined by hand with np-order's WALS
table. We have not opened any of the Qt `.ts` files or counted anything in them.

## Method (fixed now)

- Data: every `*.ts` file in the 39 repositories at their default branch on the day of the run (a
  shallow clone holding only `*.ts` files). Files that are not Qt `.ts` XML (TypeScript), copies of
  Qt's own translations (`qt_fa.ts`, `qtbase_ja.ts`, ...), English files and files whose source
  language is not English are left out.
- Messages: plural (numerus) messages and unfinished, obsolete, vanished or empty translations are left
  out. A message counts when its English source has exactly the arguments `%1` and `%2` (`%L1` too),
  each once, and so does its translation. It is reordered when the two arguments appear in a different
  order from the source.
- Shape: shape 0.1.0's `shape()` on the source text between the two arguments, after HTML tags are
  removed (`no_words`, `of`, `adposition`, `and_or`, `other`).
- Language: the `.ts` file's `language` attribute (else its file name), reduced to the base code
  (`zh_CN` -> `zh`). Clause-order groups are placeholder-order 0.1.0's; genitive order is the WALS 86A
  value in np-order 0.1.0's `languages.csv` ("Genitive-Noun" or "Noun-Genitive"; other values and
  missing languages are left out of the pools). "Not SOV" means the SVO, VSO and "no dominant order"
  groups. "Without Chinese" leaves out zh, yue and lzh.
- A pooled rate needs at least 100 valid translations, and Persian's rate at least 30, or the
  prediction using it is "not testable".
- Shape checks: six fixed strings must get their expected shape; if one fails, no prediction is scored.
- The job refuses to run until this file is on main.

## Predictions

- Q1. In SOV languages, `of` sources are reordered at least 3 times as often as `no_words` sources
  (replicates shape S1).
- Q2. In SOV languages, `no_words` sources are reordered less than 3% of the time (replicates S5).
- Q3. In languages that are not SOV, `of` sources are reordered at least 3 times as often in
  Genitive-Noun languages as in Noun-Genitive languages.
- Q4. Q3 still holds with Chinese left out.
- Q5. Persian reorders `of` sources less than 5% of the time, while SOV Genitive-Noun languages, pooled,
  reorder them more than 25% of the time.
- Q6. SOV Genitive-Noun languages reorder `of` sources more often than Genitive-Noun languages that are
  not SOV. (Genitive order alone would not explain everything.)

Q3-Q5 test the after-the-fact reading. If they fail, that reading was wrong or does not carry over
from Android to Qt projects, and we will say so.

## Limits

- WALS 86A describes a language's main genitive construction. English "of" covers counting ("%1 of
  %2"), possession and parts. Swedish and Danish count as Genitive-Noun (the s-genitive) but say "%1 av
  %2" in counting strings.
- There is only one SOV Noun-Genitive language with enough strings (Persian), so Q5 is one language,
  not a pattern.
- Strings repeat inside a project (and across its `.ts` folders); the output also gives unique-pair
  rates, repository means and repository-resampled 95% intervals.
- A translator can rewrite a whole sentence, so a kept order does not always mean the same grammar.
