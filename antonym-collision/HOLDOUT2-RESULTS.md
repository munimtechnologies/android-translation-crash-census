# antonym-collision, second held-out test: results

Graded on 2026-10-19 against the [pre-registration](HOLDOUT2-PREREG.md), which
was published on 2026-10-19 before any translation of these five projects was
read. The job (`antonym-holdout2-v3`) ran from 17:22 to 17:25 UTC in a sealed
container, with the released [l10n-guard
v0.12.0](https://github.com/munimtechnologies/l10n-guard/releases/tag/v0.12.0)
unchanged (sha256 374d8b212929d24b...). Made by MV2 of Munim, Inc. with AI
agents; H2 and H3 were graded by AI agents, not by native speakers (see
limits). Text CC BY 4.0; code Apache-2.0.

Two earlier tries of the same job did not run: `-v1`/`-v2` asked for 6 GB of
memory and no shared machine had that free. `-v3` asked for 2 GB. That changed
the job's resources only, not the code or the predictions.

## Verdicts

| | Prediction | Result | Evidence |
|---|---|---|---|
| H0 | 5 tarballs download; each has its English reference and >=10 locale files that parse | **HELD** | locale files: Jellyfin Web 105, Uptime Kuma 77, Rocket.Chat 67, Mattermost 27, Bitwarden 64; none unparsed. But see Mattermost below: it held by the letter, yet Mattermost contributed no comparison |
| H1 | >=20 warnings, from >=3 of 5 projects | **HELD** | 42 warnings, from 4 of 5 (Bitwarden, Jellyfin, Rocket.Chat, Uptime Kuma) |
| H2 | >=60% of judged non-UPLOAD sample rows are real; >=20 judged | **HELD** | 36 warnings outside the UPLOAD class, so the sample is all 36; 36 real, 0 not, 0 unsure (100%) |
| H3 | **fewer** than 50% of judged UPLOAD-class rows are real; >=5 judged | **HELD** | 6 UPLOAD warnings, all judged; 1 real, 5 not (17%) |
| H4 | >=50% of warnings have both keys as literals in the project's code | **HELD** | 25 of 42 (60%) |
| H5 | >=50% of UPLOAD-class warnings are in `fr*`/`ar*` locales; >=5 must exist | **FAILED** | 0 of 6: they are Russian (2), Ukrainian, Finnish (2) and Hungarian |

`check_catalog` and the evaluation's own call of `_antonym_collisions` agreed
on every file. The job's 12 offline tests passed.

## What the results decide (fixed in advance)

- **H3 held:** l10n-guard 0.13.0 drops the `upload`/`download` class from the
  warning's word list, with its own tests. The build is queued; it is
  released only if every existing test file and the new tests pass.
- **H2 held:** the warning stays on by default.

## What H5's failure says

The first test's hypothesis was that the upload/download false alarms come
from French and Arabic, where one noun covers transfers both ways. That was
too narrow. Here none of the 6 UPLOAD warnings was French or Arabic: Russian
*Загрузить*, Ukrainian *Завантажити* and Finnish *Lataa* are each a "load"
verb in common use for both directions, and were graded `not`. The one real
row is Hungarian, which has two words (*letöltés* down, *feltöltés* up):
Bitwarden's "Upload license" button reads *Licensz letöltése*, "download
license". So the class is unreliable across several languages, not two, and
dropping it loses some real finds like that one.

Across both held-out tests: UPLOAD class, 1 real of 12 graded; every other
class, 49 real of 49 graded (13 in the first test, 36 here).

## Per project

| Project | Commit | Antonym pairs | Comparisons | Warnings | UPLOAD | Per 1,000 comparisons |
|---|---|---|---|---|---|---|
| Jellyfin Web | ee8efb41 | 31 | 2,036 | 4 | 2 | 1.96 |
| Uptime Kuma | b092505f | 24 | 975 | 3 | 0 | 3.08 |
| Rocket.Chat | ad2047e7 | 308 | 9,960 | 29 | 2 | 2.91 |
| Mattermost | 57ea425e | (1,083) | 0 | 0 | 0 | not tested |
| Bitwarden web | 9e54ce7b | 94 | 5,965 | 6 | 2 | 1.01 |

**Mattermost was effectively not tested.** Its `en.json` is a FormatJS
descriptor file (each key maps to `{"defaultMessage": ..., "description":
...}`), while its translations map each key straight to a string. Flattened,
the English keys end in `.defaultMessage` / `.description` and no translated
key matches, so there were 0 comparisons; the 1,083 "pairs" are mostly
between descriptions. This was found after the run. It is a real gap in
l10n-guard, not only in this test: `l10n-guard json en.json de.json` on
Mattermost would report every key missing. Reading descriptor references is
a candidate for a later release, with its own test.

Identical locale files (all outside any warning): Jellyfin `ar_SA`, `ch`,
`ky`, `nds`; Uptime Kuma `ab`, `lzh`, `ne`, `ug`; Rocket.Chat `se`, `tl`;
Bitwarden `km`, `ky`, `lb`, `my`, `or`, `te`. No warning is in one of them,
so the total without duplicates is still 42. Three values carry two warnings
each (Rocket.Chat `bg` Mute/Unmute, `th-TH` Room archived/unarchived, `fi`
*Lataa*), so there are 39 distinct shared values.

## H2 and H3 hand grading

Procedure, as pre-registered: each row gets `real` (the shared value says one
side only, or neither side clearly), `not` (the value honestly covers both
states in that language) or `unsure`; the grader reads only the two English
texts, the shared value and, where needed, the key's use. Share = real /
(real + not). Verdicts and a gloss per row:
[holdout2-sample-main-graded.csv](holdout2-sample-main-graded.csv) (H2) and
[holdout2-sample-upload-graded.csv](holdout2-sample-upload-graded.csv) (H3);
the values themselves are in
[holdout2-results/warnings.csv](holdout2-results/warnings.csv).

Notable rows:

- Rocket.Chat archive notices: in `az`, `cs`, `da`, `el`, `id` (4 keys),
  `km`, `nn`, `th-TH`, `uk` and `zh-HK` the "unarchived" message says
  "archived" (14 of the 36).
- Rocket.Chat `af`, `da`, `km`, `ms-MY`: "User is unblocked" says "blocked";
  `bg`, `nn`: Unmute user says mute.
- Bitwarden `ar` and `ja`: "Confirm vault import" says export; Arabic "Data
  successfully exported" says imported.
- Uptime Kuma `sr`: Import Backup says export; `ur`: Export Backup says
  import; Bavarian (`bar`): the prompt to *enable* 2FA asks whether you want
  to switch it off.
- Jellyfin `eo`: the SpeedToSync maximum-delay setting says minimum; `ro`:
  "Airs before season" says after.
- Rocket.Chat `mn`: the offline-users count is labelled "online users";
  `ku`: Max and Min length both read "the size is {{limit}}"; Add and Remove
  user both read "select user".
- Rocket.Chat `km` *Room archived* has two zero-width spaces inside one word.

## Limits

- Grading is by AI agents working for MV2, not native speakers. Kurdish,
  Khmer, Georgian, Mongolian and Bavarian would gain most from a native
  reader; none was marked `unsure`, and the Kurdish max/min row is the least
  certain. The Russian, Ukrainian and Finnish `not` verdicts rest on common
  interface usage; a stricter reader could call Ukrainian `real`, which would
  make H3 2 of 6 (33%) and still held.
- 100% on 36 rows is a sample result, not a guarantee: 14 of the 36 are one
  class (archive) in one project.
- H4 undercounts keys built at run time (Rocket.Chat, Jellyfin).
- Mattermost was not tested (above). One commit per project.
- The 40 word classes miss antonyms outside the list by design; this measures
  precision, not recall.
- No defect here has been reported to its project yet.

## Files

From the job, in [holdout2-results/](holdout2-results/):
[warnings.csv](holdout2-results/warnings.csv) (all 42),
[sample-main.csv](holdout2-results/sample-main.csv),
[sample-upload.csv](holdout2-results/sample-upload.csv),
[summary.json](holdout2-results/summary.json) and
[stdout.txt](holdout2-results/stdout.txt). The code:
[holdout2/](holdout2/).
