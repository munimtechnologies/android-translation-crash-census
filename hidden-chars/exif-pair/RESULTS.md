# Results: the doubled zero-width space after "EXIF"

MV2, Munim, Inc. (mv2@munimtech.com). Graded 2026-10-30 (UTC). Made with AI agents.
The predictions are in [PREREG.md](PREREG.md), written and published before the job read any
repository. The verdicts below are copied unchanged from `summary.json`, which `grade()` in
`exif_pair.py` wrote. Code Apache-2.0; text and data CC BY 4.0; quoted translations stay under
their projects' licences.

## Verdicts

| | prediction | verdict |
|---|---|---|
| P1 | EXIF rate is at least 1% | **HELD** (1.59%) |
| P2 (main) | EXIF rate is at least 20 times the control rate | **HELD** (about 3,900 times) |
| P3 | every named control with at least 200 units is below 0.2% | **HELD** (highest: QR, 0.0034%) |
| P4 | in repos with an EXIF signature, fewer than half of their EXIF units carry it | **HELD** (40 of 633, 6.3%) |
| P5 | at least half of languages with at least 30 EXIF units have a signature | **FAILED** (16 of 36) |

Gate passed: both self-test repos were read (F-Droid client 28,969 units, NewPipe 56,451), and
2,391 repositories yielded units (the bar was 2,000). There were 2,517 EXIF units (the bar for
P1, P2, P4 and P5 was 100).

## Run

Job `exif-pair-v1`, sealed container, 2026-10-30 12:38-12:58 UTC; the unit tests passed first.
The job checked that PREREG.md was public before reading anything (its sha256 is in
`summary.json`). It read all 4,693 URLs in `hidden-chars/repos.txt` at each repository's latest
commit on that day: 2,391 had translations, 2,213 had none and 89 could not be cloned. None was
left unstarted. 14,145,927 translated units were read (languages that use U+200B between words
were left out, as pre-registered).

## Main numbers

| | units | with the signature | rate |
|---|---:|---:|---:|
| "EXIF" + space + word in the source | 2,517 | 40 | 1.59% |
| control: any other 2-5 letter capital word in that position | 491,777 | 2 | 0.0004% |

*Signature* = the translation has the word, one space, exactly two U+200B, then a letter.

- The 40 EXIF signatures are in **6 repositories** and **21 language codes**. 43 EXIF units have
  any U+200B at all.
- The control's two signatures are one after "QR" and one after "XML". Every one of the 16 named
  controls (GPS, PDF, URL, VPN, QR, API, HTTP, HTTPS, USB, SD, PIN, NFC, SMS, JSON, CSV, HTML)
  has thousands of units and zero signatures, apart from QR (1 of 29,036).
- Across the whole corpus, 532 units have the space-pair-letter shape after any word. 40 of them
  (7.5%) follow "EXIF", a word in only 2,517 of 14.1 million units.
- Mixed-case "Exif" (exploratory): 468 units, **0** signatures.

### Repositories with at least one EXIF signature

| repository | EXIF units | signatures |
|---|---:|---:|
| ramack/ActivityDiary | 42 | 24 |
| firebirdberlin/nightdream | 68 | 8 |
| luca/Kompact (git.naxod.com) | 48 | 3 |
| commons-app/apps-android-commons | 104 | 3 |
| d4rken-org/sdmaid-se | 357 | 1 |
| tenzap/exif-thumbnail-adder | 14 | 1 |
| **total** | **633** | **40** |

### Languages with at least 30 EXIF units (P5)

With a signature (16): ar 2/61, ca 2/61, cs 2/61, da 1/53, es 2/85, fa 1/54, fr 2/78, hu 3/61,
it 2/71, ko 2/64, nl 1/62, pl 3/77, pt 3/88, ro 1/61, sv 1/60, tr 4/72.

Without (20): be 52, bn 48, de 78, et 49, fi 57, fil 47, hi 50, in 56, iw 51, ja 69, kk 42, lt 49,
ru 74, sk 53, sr 57, ta 48, te 49, uk 63, vi 59, zh 145.

Languages under 30 units with a signature: bg 1/7, el 2/18, ga 1/6, hr 3/10, no 1/2.

## Reading

The doubled zero-width space is not spread evenly over technical abbreviations: after "EXIF" it
is about 3,900 times as common as after any other short capital word in the same position, and
the most common abbreviations (QR, VPN, API, URL, GPS) almost never carry it. Even inside the six
apps that have it, most translations of "EXIF" are clean (P4), so it marks particular
translation batches, not a habit of whole projects.

P5 failed: the signature is not found in most languages. The post-hoc notes below suggest part
of the reason is how a language writes "EXIF tags", but that was not tested.

## Post hoc and exploratory (not pre-registered)

- **One app carries much of P1.** Without ActivityDiary (24 of 42 units), the EXIF rate is 16 of
  2,475, 0.65%, which is below P1's 1% bar. That would still be about 1,600 times the control rate.
  This is arithmetic on the published counts, done after grading.
- **The word after "EXIF" in the source** (from `summary.json`): "tags" 14 of 98, "tag" 14 of 25,
  "information" 8 of 68, "metadata" 3 of 498, "user" 1 of 72. Every other next word has 0.
- **Languages that join the words cannot show the shape.** We read ActivityDiary's 18 EXIF units
  without the signature in `exif_units.csv`. 12 write "EXIF" with no space after it: a hyphen
  compound (da "EXIF-tags", de "EXIF-Attribut", fi, nl, no, sv, ru "EXIF-теге") or no spaces at
  all (ja "EXIFタグ"). In the Russian `setting_tag_no` the pair is still there, but after "для "
  rather than after "EXIF". This may explain part of P5's failure (German, Russian, Japanese and
  Chinese have 0), but it was not measured across the corpus.
- **Why this differs from the earlier post-hoc count of 41.** That count (in
  [ZWSP-SIGNATURE.md](../zwsp-signature/ZWSP-SIGNATURE.md)) was a text search over `hits.csv`,
  which keeps only U+200B-only rows and cuts targets at about 200 characters. Here, Twig's
  Russian row is not an EXIF unit because its English source says "EXIF-embedded" (a hyphen, not
  a space). The Vietnamese row with four U+200B is not a signature, which needs exactly two.
  exif-thumbnail-adder's Turkish row is new: its pair sits past the 200-character cut.

## Limits

- The numerator was roughly known in advance (41 rows, see PREREG.md); the denominators and
  every control were not.
- Observational. It shows where the pair clusters, not which tool put it there. The shape
  matches a 2017 Google Translate API report, but that does not prove the origin of any string.
- Repositories were read at their latest commit on 2026-10-30, not at the census snapshot.
  Nightdream still had 8 signatures at commit 78f9ca5 (MV2 reported them in its issue #389 the
  same day).
- One app (ActivityDiary) holds 24 of the 40 signatures. No native speaker checked the units.

## Files

- `summary.json`: every count and verdict (written by the job; PREREG sha256 and repos.txt sha256
  inside).
- `exif_units.csv`: every EXIF and Exif unit with repo, commit, key, source and target (U+200B
  shown as `<U+200B>`).
- `words.csv`: units, signatures, any-U+200B and repo count for every capital word.
- `repos.jsonl`: status, commit and EXIF counts for each repository.

Reproduce: `python exif_pair.py --out-dir out` (Python standard library and git).

MV2, Munim, Inc., mv2@munimtech.com
