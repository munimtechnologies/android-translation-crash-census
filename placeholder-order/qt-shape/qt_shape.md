# qt-shape 0.1.0: does genitive order decide which "X of Y" strings translators reorder?

MV2 of Munim, Inc., made with AI agents. Qt .ts files of 39 of 39 repositories, read 2026-10-17T08:28:54+00:00.

- Shape checks: all passed

## Predictions

- Q1 NOT TESTABLE: in SOV languages, of sources are reordered at least 3x as often as no_words sources. of n/a, no_words 0.4%
- Q2 HELD: in SOV languages, no_words sources are reordered less than 3% of the time. no_words 0.4%
- Q3 HELD: in languages that are not SOV, of sources are reordered at least 3x as often in Genitive-Noun languages as in Noun-Genitive languages. GenN 12.9%, NGen 0.0%
- Q4 NOT TESTABLE: Q3 holds with Chinese left out. GenN n/a, NGen 0.0%
- Q5 NOT TESTABLE: Persian reorders of sources less than 5% of the time, while SOV Genitive-Noun languages reorder them more than 25% of the time. fa n/a, SOV GenN n/a
- Q6 NOT TESTABLE: SOV Genitive-Noun languages reorder of sources more often than Genitive-Noun languages that are not SOV. SOV GenN n/a, non-SOV GenN 12.9%

## Reorder rate by shape (sources with exactly %1 and %2)

| scope | shape | valid | reordered | rate | 95% CI (repos) | repo mean | unique-pair rate | repos |
|---|---|---:|---:|---:|---|---:|---:|---:|
| all | no_words | 9349 | 24 | 0.3% | 0.1%-0.4% | 0.2% | 0.3% | 33 |
| all | of | 745 | 70 | 9.4% | 6.3%-12.0% | 7.3% | 10.0% | 14 |
| all | adposition | 1672 | 116 | 6.9% | 4.2%-9.4% | 5.6% | 7.1% | 20 |
| all | and_or | 652 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 12 |
| all | other | 17241 | 321 | 1.9% | 0.9%-3.7% | 2.5% | 2.0% | 35 |
| all | total | 29659 | 531 | 1.8% | 1.1%-2.8% | 1.5% | 2.0% | 36 |
| SOV | no_words | 1384 | 6 | 0.4% | 0.1%-1.0% | 0.6% | 0.5% | 32 |
| SOV | of | 94 | 52 | 55.3% | 42.6%-63.8% | 53.9% | 54.7% | 11 |
| SOV | adposition | 258 | 62 | 24.0% | 13.4%-36.0% | 22.5% | 24.2% | 17 |
| SOV | and_or | 107 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 10 |
| SOV | other | 2690 | 107 | 4.0% | 2.1%-7.7% | 7.8% | 4.1% | 34 |
| SOV | total | 4533 | 227 | 5.0% | 3.1%-7.8% | 5.0% | 5.3% | 35 |
| SVO | no_words | 6529 | 17 | 0.3% | 0.1%-0.5% | 0.2% | 0.3% | 33 |
| SVO | of | 529 | 18 | 3.4% | 1.3%-5.5% | 2.3% | 3.5% | 14 |
| SVO | adposition | 1126 | 46 | 4.1% | 1.9%-6.2% | 4.2% | 4.0% | 20 |
| SVO | and_or | 451 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 12 |
| SVO | other | 11944 | 180 | 1.5% | 0.6%-3.3% | 1.8% | 1.6% | 35 |
| SVO | total | 20579 | 261 | 1.3% | 0.7%-2.3% | 1.1% | 1.4% | 36 |
| VSO | no_words | 130 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 15 |
| VSO | of | 13 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 5 |
| VSO | adposition | 32 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 9 |
| VSO | and_or | 11 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 5 |
| VSO | other | 214 | 7 | 3.3% | 0.7%-5.5% | 1.8% | 3.4% | 14 |
| VSO | total | 400 | 7 | 1.8% | 0.3%-3.1% | 1.0% | 1.9% | 15 |
| no dominant order | no_words | 817 | 1 | 0.1% | 0.0%-0.4% | 0.1% | 0.2% | 33 |
| no dominant order | of | 60 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 13 |
| no dominant order | adposition | 138 | 4 | 2.9% | 0.0%-6.7% | 2.4% | 2.4% | 20 |
| no dominant order | and_or | 57 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 12 |
| no dominant order | other | 1472 | 24 | 1.6% | 0.3%-3.6% | 1.1% | 1.5% | 35 |
| no dominant order | total | 2544 | 29 | 1.1% | 0.3%-2.3% | 0.8% | 1.1% | 36 |
| unassigned | no_words | 489 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 27 |
| unassigned | of | 49 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 9 |
| unassigned | adposition | 118 | 4 | 3.4% | 0.0%-10.2% | 1.7% | 3.6% | 15 |
| unassigned | and_or | 26 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 7 |
| unassigned | other | 921 | 3 | 0.3% | 0.0%-0.8% | 0.0% | 0.3% | 29 |
| unassigned | total | 1603 | 7 | 0.4% | 0.0%-1.0% | 0.1% | 0.5% | 30 |
| pool:SOV:GenN | no_words | 1183 | 3 | 0.3% | 0.0%-0.6% | 0.4% | 0.3% | 32 |
| pool:SOV:GenN | of | 76 | 46 | 60.5% | 45.1%-69.2% | 56.0% | 60.9% | 11 |
| pool:SOV:GenN | adposition | 206 | 57 | 27.7% | 15.3%-41.2% | 25.6% | 27.9% | 17 |
| pool:SOV:GenN | and_or | 95 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 10 |
| pool:SOV:GenN | other | 2289 | 103 | 4.5% | 2.3%-8.6% | 8.3% | 4.6% | 34 |
| pool:SOV:GenN | total | 3849 | 209 | 5.4% | 3.4%-8.4% | 5.4% | 5.8% | 35 |
| pool:SOV:NGen | no_words | 80 | 2 | 2.5% | 0.0%-10.2% | 5.0% | 3.1% | 10 |
| pool:SOV:NGen | of | 9 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 4 |
| pool:SOV:NGen | adposition | 16 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 7 |
| pool:SOV:NGen | and_or | 4 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 3 |
| pool:SOV:NGen | other | 114 | 1 | 0.9% | 0.0%-2.6% | 0.4% | 1.0% | 11 |
| pool:SOV:NGen | total | 223 | 3 | 1.3% | 0.0%-3.9% | 1.3% | 1.5% | 12 |
| pool:nonSOV:GenN | no_words | 1624 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 33 |
| pool:nonSOV:GenN | of | 139 | 18 | 12.9% | 6.2%-22.5% | 12.6% | 12.6% | 11 |
| pool:nonSOV:GenN | adposition | 284 | 44 | 15.5% | 7.9%-21.3% | 9.6% | 15.0% | 19 |
| pool:nonSOV:GenN | and_or | 125 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 11 |
| pool:nonSOV:GenN | other | 3039 | 85 | 2.8% | 1.0%-6.7% | 5.1% | 3.0% | 35 |
| pool:nonSOV:GenN | total | 5211 | 147 | 2.8% | 1.4%-5.0% | 2.5% | 3.1% | 36 |
| pool:nonSOV:NGen | no_words | 4293 | 11 | 0.3% | 0.0%-0.5% | 0.2% | 0.2% | 33 |
| pool:nonSOV:NGen | of | 306 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 14 |
| pool:nonSOV:NGen | adposition | 718 | 5 | 0.7% | 0.0%-2.1% | 1.4% | 0.8% | 20 |
| pool:nonSOV:NGen | and_or | 282 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 12 |
| pool:nonSOV:NGen | other | 7331 | 101 | 1.4% | 0.4%-2.9% | 0.9% | 1.5% | 35 |
| pool:nonSOV:NGen | total | 12930 | 117 | 0.9% | 0.3%-1.8% | 0.7% | 1.0% | 36 |
| pool:nonSOV:GenN:nozh | no_words | 1031 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 31 |
| pool:nonSOV:GenN:nozh | of | 95 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 10 |
| pool:nonSOV:GenN:nozh | adposition | 169 | 12 | 7.1% | 2.1%-10.5% | 3.5% | 7.0% | 17 |
| pool:nonSOV:GenN:nozh | and_or | 80 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 10 |
| pool:nonSOV:GenN:nozh | other | 1844 | 34 | 1.8% | 0.2%-5.4% | 1.3% | 1.9% | 34 |
| pool:nonSOV:GenN:nozh | total | 3219 | 46 | 1.4% | 0.3%-3.6% | 0.8% | 1.6% | 35 |
| pool:nonSOV:NGen:nozh | no_words | 4293 | 11 | 0.3% | 0.0%-0.5% | 0.2% | 0.2% | 33 |
| pool:nonSOV:NGen:nozh | of | 306 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 14 |
| pool:nonSOV:NGen:nozh | adposition | 718 | 5 | 0.7% | 0.0%-2.1% | 1.4% | 0.8% | 20 |
| pool:nonSOV:NGen:nozh | and_or | 282 | 0 | 0.0% | 0.0%-0.0% | 0.0% | 0.0% | 12 |
| pool:nonSOV:NGen:nozh | other | 7331 | 101 | 1.4% | 0.4%-2.9% | 0.9% | 1.5% | 35 |
| pool:nonSOV:NGen:nozh | total | 12930 | 117 | 0.9% | 0.3%-1.8% | 0.7% | 1.0% | 36 |

## Languages (100+ translations): reorder rate by shape (valid in brackets)

| lang | group | WALS 86A | all | no_words | of | adposition | and_or | other |
|---|---|---|---|---|---|---|---|---|
| ta | SOV | Genitive-Noun | 8.5% (118) | 0.0% (48) | 0.0% (1) | 20.0% (5) | 0.0% (2) | 14.5% (62) |
| ko | SOV | Genitive-Noun | 7.4% (857) | 0.0% (271) | 82.4% (17) | 40.4% (47) | 0.0% (20) | 6.0% (502) |
| ja | SOV | Genitive-Noun | 7.1% (798) | 0.4% (262) | 61.9% (21) | 31.1% (45) | 0.0% (20) | 6.4% (450) |
| tr | SOV | Genitive-Noun | 5.6% (753) | 0.4% (248) | 25.0% (16) | 40.0% (45) | 0.0% (20) | 4.5% (424) |
| zh | SVO | Genitive-Noun | 5.1% (1992) | 0.0% (593) | 40.9% (44) | 27.8% (115) | 0.0% (45) | 4.3% (1195) |
| pa | SOV | Genitive-Noun | 4.9% (102) | 0.0% (35) | 100.0% (2) | 0.0% (7) | 0.0% (1) | 5.3% (57) |
| hi | SOV | Genitive-Noun | 4.0% (125) | 0.0% (36) | 100.0% (2) | 16.7% (6) | 0.0% (3) | 2.6% (78) |
| eu | SOV | Genitive-Noun | 3.7% (323) | 0.0% (83) | 58.3% (12) | 7.1% (14) | 0.0% (15) | 2.0% (199) |
| he | SVO | Noun-Genitive | 3.1% (393) | 4.1% (122) | 0.0% (8) | 0.0% (21) | 0.0% (8) | 3.0% (234) |
| eo | SVO | - | 2.7% (150) | 7.8% (51) | 0.0% (6) | 0.0% (8) | 0.0% (1) | 0.0% (84) |
| ca | SVO | Noun-Genitive | 2.1% (561) | 0.6% (178) | 0.0% (13) | 3.6% (28) | 0.0% (10) | 3.0% (332) |
| fi | SVO | Genitive-Noun | 2.0% (544) | 0.0% (186) | 0.0% (16) | 10.7% (28) | 0.0% (14) | 2.7% (300) |
| da | SVO | Genitive-Noun | 1.9% (377) | 0.0% (113) | 0.0% (13) | 0.0% (23) | 0.0% (11) | 3.2% (217) |
| it | SVO | Noun-Genitive | 1.8% (987) | 0.3% (331) | 0.0% (21) | 2.2% (46) | 0.0% (20) | 2.8% (569) |
| hu | no dominant order | Genitive-Noun | 1.8% (619) | 0.0% (191) | 0.0% (15) | 12.9% (31) | 0.0% (17) | 1.9% (365) |
| az | SOV | Genitive-Noun | 1.7% (242) | 0.0% (72) | 100.0% (3) | 0.0% (4) | n/a (0) | 0.6% (163) |
| ga | VSO | Noun-Genitive | 1.6% (189) | 0.0% (71) | 0.0% (8) | 0.0% (14) | 0.0% (6) | 3.3% (90) |
| sq | SVO | Noun-Genitive | 1.5% (194) | 0.0% (63) | 0.0% (2) | 9.1% (11) | 0.0% (6) | 1.8% (112) |
| et | SVO | Genitive-Noun | 1.5% (326) | 0.0% (94) | 0.0% (10) | 18.8% (16) | 0.0% (8) | 1.0% (198) |
| ru | SVO | Noun-Genitive | 1.5% (983) | 0.0% (319) | 0.0% (20) | 1.8% (55) | 0.0% (24) | 2.5% (565) |
| ka | SOV | Genitive-Noun | 1.4% (139) | 0.0% (46) | 50.0% (2) | 0.0% (7) | 0.0% (5) | 1.3% (79) |
| fa | SOV | Noun-Genitive | 1.3% (223) | 2.5% (80) | 0.0% (9) | 0.0% (16) | 0.0% (4) | 0.9% (114) |
| nl | no dominant order | Noun-Genitive | 1.2% (757) | 0.0% (238) | 0.0% (17) | 0.0% (44) | 0.0% (18) | 2.0% (440) |
| fr | SVO | Noun-Genitive | 1.1% (1071) | 0.0% (354) | 0.0% (21) | 1.6% (61) | 0.0% (28) | 1.8% (607) |
| cs | SVO | - | 1.0% (860) | 0.0% (283) | 0.0% (19) | 0.0% (49) | 0.0% (17) | 1.8% (492) |
| lv | SVO | Genitive-Noun | 1.0% (200) | 0.0% (62) | 0.0% (8) | 16.7% (6) | 0.0% (2) | 0.8% (122) |
| sv | SVO | Genitive-Noun | 1.0% (810) | 0.0% (279) | 0.0% (20) | 0.0% (38) | 0.0% (21) | 1.8% (452) |
| ne | SOV | Genitive-Noun | 1.0% (103) | 0.0% (5) | n/a (0) | 0.0% (3) | n/a (0) | 1.1% (95) |
| uk | SVO | - | 0.9% (691) | 0.0% (217) | 0.0% (18) | 2.1% (47) | 0.0% (15) | 1.3% (394) |
| sl | SVO | - | 0.8% (373) | 0.0% (105) | 0.0% (14) | 0.0% (18) | 0.0% (15) | 1.4% (221) |
| de | no dominant order | Noun-Genitive | 0.8% (1168) | 0.3% (388) | 0.0% (28) | 0.0% (63) | 0.0% (22) | 1.2% (667) |
| es | SVO | Noun-Genitive | 0.6% (1829) | 0.3% (734) | 0.0% (50) | 0.0% (88) | 0.0% (33) | 1.0% (924) |
| lt | SVO | Genitive-Noun | 0.6% (343) | 0.0% (106) | 0.0% (13) | 3.7% (27) | 0.0% (7) | 0.5% (190) |
| ro | SVO | Noun-Genitive | 0.6% (352) | 1.0% (103) | 0.0% (7) | 0.0% (29) | 0.0% (9) | 0.5% (204) |
| sr | SVO | - | 0.5% (613) | 1.2% (167) | 0.0% (20) | 0.0% (27) | 0.0% (16) | 0.3% (383) |
| hr | SVO | - | 0.5% (429) | 0.0% (108) | 0.0% (13) | 0.0% (19) | 0.0% (8) | 0.7% (281) |
| pl | SVO | Noun-Genitive | 0.5% (888) | 0.0% (271) | 0.0% (19) | 0.0% (45) | 0.0% (21) | 0.8% (532) |
| lo | SVO | Noun-Genitive | 0.4% (237) | 0.0% (79) | 0.0% (10) | 0.0% (21) | 0.0% (11) | 0.9% (116) |
| th | SVO | Noun-Genitive | 0.4% (243) | 0.0% (80) | 0.0% (2) | 0.0% (12) | 0.0% (6) | 0.7% (143) |
| gl | SVO | - | 0.3% (373) | 0.0% (84) | 0.0% (11) | 0.0% (19) | 0.0% (5) | 0.4% (254) |
| el | unassigned | Noun-Genitive | 0.2% (515) | 0.0% (155) | 0.0% (15) | 0.0% (37) | 0.0% (8) | 0.3% (300) |
| pt | SVO | Noun-Genitive | 0.2% (1764) | 0.0% (576) | 0.0% (38) | 0.0% (101) | 0.0% (28) | 0.3% (1021) |
| ar | unassigned | Noun-Genitive | 0.0% (410) | 0.0% (122) | 0.0% (13) | 0.0% (20) | 0.0% (9) | 0.0% (246) |
| be | SVO | Noun-Genitive | 0.0% (217) | 0.0% (52) | 0.0% (5) | 0.0% (6) | 0.0% (5) | 0.0% (149) |
| bg | SVO | - | 0.0% (427) | 0.0% (137) | 0.0% (12) | 0.0% (27) | 0.0% (7) | 0.0% (244) |
| bs | SVO | - | 0.0% (144) | 0.0% (20) | 0.0% (4) | 0.0% (2) | n/a (0) | 0.0% (118) |
| id | SVO | Noun-Genitive | 0.0% (440) | 0.0% (156) | 0.0% (14) | 0.0% (23) | 0.0% (14) | 0.0% (233) |
| kab | unassigned | Noun-Genitive | 0.0% (124) | 0.0% (37) | 0.0% (9) | 0.0% (14) | 0.0% (2) | 0.0% (62) |
| nb | SVO | - | 0.0% (379) | 0.0% (99) | 0.0% (10) | 0.0% (16) | 0.0% (8) | 0.0% (246) |
| sk | SVO | - | 0.0% (425) | 0.0% (106) | 0.0% (14) | 0.0% (24) | 0.0% (9) | 0.0% (272) |
| vi | SVO | Noun-Genitive | 0.0% (332) | 0.0% (85) | 0.0% (4) | 0.0% (25) | 0.0% (6) | 0.0% (212) |

## Most often reordered sources: SOV

| source | shape | translations | reordered | repos |
|---|---|---:|---:|---:|
| `Cannot %1 device %2` | other | 38 | 9 | 1 |
| `Syncing %1 of %2` | of | 12 | 8 | 1 |
| `%1 of %2` | of | 16 | 6 | 4 |
| `%1 processed out of %2 selected` | other | 6 | 5 | 1 |
| `Enter username and password for "%1" at %2.` | adposition | 6 | 5 | 1 |
| `Multiple import source path to %1 in %2` | adposition | 5 | 5 | 1 |
| `%1 on %2` | adposition | 44 | 4 | 1 |
| `%1 in %2` | adposition | 8 | 4 | 1 |
| `<qt>Enter username and password for "%1" at %2</qt>` | adposition | 6 | 4 | 1 |
| `Look up "%1" in %2` | adposition | 6 | 4 | 1 |
| `Results (showing <i>%1</i> out of <i>%2</i>):` | of | 6 | 4 | 1 |
| `Syncing %1 of %2 (A few seconds left)` | of | 6 | 4 | 1 |
| `Syncing file %1 of %2` | of | 6 | 4 | 1 |
| `%1 of %2 in use` | of | 5 | 4 | 1 |
| `-- Using script %1 to read %2` | other | 5 | 4 | 1 |
| `-- Using script %1 to write %2` | other | 5 | 4 | 1 |
| `Conflicting export target path %1 in %2` | adposition | 5 | 4 | 1 |
| `Successfully removed attachment %1 from entry %2.` | other | 5 | 4 | 1 |
| `SymmetricCipher::init: Invalid IV size of %1 for %2.` | adposition | 5 | 4 | 1 |
| `Patched %1 of %2 selected instructions.` | of | 4 | 4 | 1 |
| `requesting alias(%1) for unknown command(%2): ignored` | other | 8 | 3 | 1 |
| `History size: %1 entries out of maximum %2` | other | 6 | 3 | 1 |
| `Incorrect update info received for %1 out of %2 plugins.` | of | 6 | 3 | 1 |
| `Look up "%1" in %2 in &New Tab` | adposition | 6 | 3 | 1 |
| `Server configuration error: %1 at %2.` | adposition | 6 | 3 | 1 |

## Most often reordered sources: fa

| source | shape | translations | reordered | repos |
|---|---|---:|---:|---:|
| `%1%2%` | no_words | 1 | 1 | 1 |
| `Cannot %1 device %2` | other | 1 | 1 | 1 |
| `Result for equation: %1 = %2` | no_words | 1 | 1 | 1 |
| `%1 (%2)` | no_words | 5 | 0 | 4 |
| `%1: %2` | no_words | 4 | 0 | 3 |
| `%1 and %2` | and_or | 3 | 0 | 2 |
| `%1 %2` | no_words | 2 | 0 | 2 |
| `%1 (%2 avg.)` | no_words | 2 | 0 | 1 |
| `%1 (%2 colors)` | no_words | 2 | 0 | 1 |
| `%1 (%2 max)` | no_words | 2 | 0 | 1 |
| `%1 (%2 this session)` | no_words | 2 | 0 | 1 |
| `%1 (%2 total)` | no_words | 2 | 0 | 1 |
| `%1 [%2]` | no_words | 2 | 0 | 1 |
| `%1 has been selected for %2` | other | 2 | 0 | 1 |
| `%1 of %2` | of | 2 | 0 | 2 |
| `%1 on %2` | adposition | 2 | 0 | 1 |
| `%1 saved to %2` | other | 2 | 0 | 1 |
| `%1's %2 has been changed` | other | 2 | 0 | 1 |
| `%1d %2h` | other | 2 | 0 | 1 |
| `%1h %2m` | other | 2 | 0 | 1 |
| `%1y %2d` | other | 2 | 0 | 1 |
| `%L1h %L2m` | other | 2 | 0 | 1 |
| `%L1m %L2s` | other | 2 | 0 | 1 |
| `%L2m %L1s` | other | 2 | 0 | 1 |
| `File <strong>%1</strong> already exists, you need to remove it before choosing <strong>%2</strong> as new filename!` | other | 2 | 0 | 1 |

## Most often reordered sources: zh

| source | shape | translations | reordered | repos |
|---|---|---:|---:|---:|
| `%1 on %2` | adposition | 6 | 6 | 1 |
| `%1 muted and deafened by %2.` | other | 3 | 3 | 1 |
| `%1 unmuted and undeafened by %2.` | other | 3 | 3 | 1 |
| `Incorrect update info received for %1 out of %2 plugins.` | of | 3 | 3 | 1 |
| `Partial capo: Fret %1 on strings %2` | other | 3 | 3 | 1 |
| `You are already syncing the subfolder %1 at %2.` | adposition | 3 | 3 | 1 |
| `You have been logged out of your account %1 at %2. Please login again.` | adposition | 3 | 3 | 1 |
| `You were denied %1 privileges in %2.` | other | 3 | 3 | 1 |
| `%1 of %2` | of | 7 | 2 | 3 |
| `%1 of %2 in use` | of | 3 | 2 | 1 |
| `%1 suppressed by %2.` | other | 3 | 2 | 1 |
| `Enter username and password for "%1" at %2.` | adposition | 3 | 2 | 1 |
| `Results (showing <i>%1</i> out of <i>%2</i>):` | of | 3 | 2 | 1 |
| `Syncing file %1 of %2` | of | 3 | 2 | 1 |
| `Timeout while trying to connect to %1 at %2.` | adposition | 3 | 2 | 1 |
| `You were moved to %1 by %2.` | adposition | 3 | 2 | 1 |
| `%1 at %2` | adposition | 2 | 2 | 1 |
| `%1 of %2 - Stopped` | of | 2 | 2 | 1 |
| `%1 results in %2` | other | 2 | 2 | 1 |
| `%1 unsuppressed by %2.` | other | 2 | 2 | 1 |
| `<html><p>The href <b>%1</b> found in <b>%2</b> does not exist (and there may be more). Splitting or merging under these ` | other | 2 | 2 | 1 |
| `Failed to apply masterpage '%1' on page: %2` | other | 2 | 2 | 1 |
| `Go to Page %1 in File %2` | other | 2 | 2 | 1 |
| `Look up "%1" in %2` | adposition | 2 | 2 | 1 |
| `Look up "%1" in %2 in &New Tab` | adposition | 2 | 2 | 1 |

## Repositories

| repo | status | commit | .ts files | languages | two-argument valid |
|---|---|---|---:|---:|---:|
| qbittorrent/qBittorrent | ok | df402f91d4 | 116 | 54 | 5092 |
| keepassxreboot/keepassxc | ok | 5abafd2805 | 45 | 42 | 1712 |
| nextcloud/desktop | ok | 372e36d5ab | 62 | 49 | 2728 |
| musescore/MuseScore | ok | 4509c9072c | 136 | 59 | 1023 |
| mumble-voip/mumble | ok | 9ef78aac07 | 43 | 40 | 938 |
| flameshot-org/flameshot | ok | 4bc3acacf0 | 48 | 44 | 250 |
| hluk/CopyQ | ok | ef1fb57775 | 34 | 32 | 107 |
| Mudlet/Mudlet | ok | 705c1831f7 | 22 | 18 | 1251 |
| mltframework/shotcut | ok | 1c10771d42 | 40 | 36 | 718 |
| PCSX2/pcsx2 | ok | 091ab68708 | 41 | 38 | 909 |
| stenzek/duckstation | ok | d708117400 | 19 | 17 | 987 |
| mapeditor/tiled | ok | 221be2066c | 28 | 26 | 632 |
| LibreCAD/LibreCAD | ok | 193a366d14 | 127 | 42 | 814 |
| bitcoin/bitcoin | ok | 924f4c4ac7 | 100 | 85 | 696 |
| monero-project/monero-gui | ok | ac86e61e30 | 48 | 46 | 213 |
| Sigil-Ebook/Sigil | ok | 3df3d1a207 | 20 | 19 | 100 |
| LMMS/lmms | ok | a2f57e70ce | 38 | 37 | 390 |
| Cockatrice/Cockatrice | ok | a139084ad6 | 46 | 21 | 423 |
| lxqt/lxqt-panel | ok | 9be51d5f0f | 1036 | 52 | 185 |
| lxqt/pcmanfm-qt | ok | 94fa2c173f | 55 | 51 | 40 |
| lxqt/qterminal | ok | 2dbef60e67 | 47 | 44 | 0 |
| wireshark/wireshark | ok | e2a6c737d7 | 17 | 17 | 423 |
| scribusproject/scribus | ok | f979aa1437 | 71 | 62 | 1605 |
| AntiMicroX/antimicrox | ok | b5fb5947d6 | 29 | 27 | 138 |
| Qalculate/qalculate-qt | ok | 77d5eb9345 | 13 | 11 | 25 |
| qTox/qTox | ok | 2b9cbdcac1 | 53 | 49 | 210 |
| tsujan/FeatherPad | ok | d9ae18ad79 | 39 | 37 | 0 |
| ksnip/ksnip | ok | df69d12a08 | 39 | 36 | 65 |
| nomacs/nomacs | ok | 251d54771f | 30 | 28 | 402 |
| hydrogen-music/hydrogen | ok | 00509be4aa | 19 | 19 | 22 |
| smplayer-dev/smplayer | ok | cbca1020de | 48 | 44 | 615 |
| pbek/QOwnNotes | ok | 4f01d588ca | 68 | 66 | 836 |
| xiaoyifang/goldendict-ng | ok | 5b1badeace | 42 | 37 | 706 |
| fritzing/fritzing-app | ok | 5aa56a5101 | 39 | 36 | 1199 |
| subsurface/subsurface | ok | 782bff15e2 | 31 | 29 | 291 |
| tumic0/GPXSee | ok | 91e4c0cac6 | 19 | 19 | 0 |
| savoirfairelinux/jami-client-qt | ok | dd71cffd31 | 116 | 69 | 577 |
| linuxdeepin/dde-file-manager | ok | f17ca8f51d | 473 | 72 | 2082 |
| FreeCAD/FreeCAD | ok | 088f49373d | 1204 | 44 | 1255 |
