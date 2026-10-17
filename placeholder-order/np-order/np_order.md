# np-order 0.1.0: noun-phrase order and placeholder reordering

MV2 of Munim, Inc., made with AI agents. WALS data: Dryer & Haspelmath (eds.) 2013, CC BY 4.0.

- Languages with at least 300 numbered translations in at least 10 repositories: 75
- Mapping checks: all passed

## Predictions

- P1 FAILED: genitive order (86A) separates reorder rates better than verb-final order (81A). AUC 0.924 vs 0.988 on 46 languages (sides [[24, 22], [18, 28]]), difference 95% CI [-0.162, 0.008]
- P2 FAILED: adposition order (85A) separates reorder rates better than verb-final order (81A). AUC 0.983 vs 0.995 on 50 languages (sides [[18, 32], [17, 33]]), difference 95% CI [-0.050, 0.010]
- P3 NOT TESTABLE: among SOV languages, noun-genitive ones reorder less (median) than genitive-noun ones. median 0.1474 (az eu hi ja ka kn ko ml mr my ne pa ta te tr ur uz) vs 0.0287 (fa)
- P4 HELD: among SVO/VSO/VOS languages other than zh and yue, genitive-noun ones reorder more (median) than noun-genitive ones. median 0.0156 (da et fi lt lv sv) vs 0.0044 (ca cy es fil fr ga he id is it kab lo pl pt ro ru sq sw th vi zu)
- P5 HELD: genitive order (86A) separates reorder rates better than adjective order (87A). AUC 0.926 vs 0.821 on 53 languages (sides [[26, 27], [31, 22]]), difference 95% CI [0.008, 0.224]

## Each feature alone (all languages with a value)

| feature | positive | negative | AUC | AUC unique pairs | AUC repo mean |
|---|---:|---:|---:|---:|---:|
| 81A SOV | 22 | 35 | 0.992 | 0.995 | 0.987 |
| 85A Postpositions | 20 | 37 | 0.982 | 0.993 | 0.970 |
| 86A Genitive-Noun | 26 | 28 | 0.926 | 0.931 | 0.919 |
| 87A Adjective-Noun | 40 | 22 | 0.765 | 0.786 | 0.767 |
| 90A Relative clause-Noun | 11 | 41 | 0.987 | 0.987 | 0.993 |

## Languages

| lang | valid | reorder rate | 81A | 85A | 86A | 87A | 90A |
|---|---:|---:|---|---|---|---|---|
| my | 439 | 0.2164 | SOV | Postpositions | Genitive-Noun | Noun-Adjective | Relative clause-Noun |
| mr | 573 | 0.1867 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Relative clause-Noun |
| kn | 681 | 0.1806 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Mixed |
| gu | 506 | 0.1798 | SOV | Postpositions |  | Adjective-Noun |  |
| ne | 437 | 0.1739 | SOV | Postpositions | Genitive-Noun | Adjective-Noun |  |
| te | 842 | 0.1734 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Relative clause-Noun |
| hi | 2360 | 0.1619 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Correlative |
| or | 385 | 0.1610 | SOV |  |  |  | Correlative |
| ko | 3976 | 0.1602 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Relative clause-Noun |
| pa | 795 | 0.1484 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Mixed |
| ml | 970 | 0.1474 | SOV |  | Genitive-Noun | Adjective-Noun | Relative clause-Noun |
| si | 369 | 0.1301 | SOV | Postpositions |  | Adjective-Noun | Noun-Relative clause |
| bn | 1786 | 0.1277 | SOV |  |  |  |  |
| ja | 4868 | 0.1194 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Relative clause-Noun |
| ta | 1752 | 0.1187 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Relative clause-Noun |
| tr | 4601 | 0.1152 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Relative clause-Noun |
| kk | 431 | 0.1114 |  |  |  |  |  |
| ur | 990 | 0.1010 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Correlative |
| uz | 408 | 0.0931 | SOV |  | Genitive-Noun | Adjective-Noun | Relative clause-Noun |
| az | 930 | 0.0892 | SOV |  | Genitive-Noun | Adjective-Noun | Mixed |
| zh | 11325 | 0.0771 | SVO | No dominant order | Genitive-Noun | Adjective-Noun | Relative clause-Noun |
| eu | 1440 | 0.0625 | SOV | Postpositions | Genitive-Noun | Noun-Adjective | Relative clause-Noun |
| hu | 3201 | 0.0306 | No dominant order | Postpositions | Genitive-Noun | Adjective-Noun | Mixed |
| et | 2438 | 0.0295 | SVO | Postpositions | Genitive-Noun | Adjective-Noun | Noun-Relative clause |
| fa | 2582 | 0.0287 | SOV | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| lt | 1941 | 0.0222 | SVO | Prepositions | Genitive-Noun | Adjective-Noun | Noun-Relative clause |
| ka | 782 | 0.0217 | SOV | Postpositions | Genitive-Noun | Adjective-Noun | Noun-Relative clause |
| hy | 372 | 0.0215 | No dominant order | Postpositions | Genitive-Noun | Adjective-Noun | Mixed |
| lv | 1335 | 0.0210 | SVO | Prepositions | Genitive-Noun | Adjective-Noun | Noun-Relative clause |
| sk | 2434 | 0.0152 |  |  |  |  |  |
| cs | 3950 | 0.0152 | SVO | Prepositions | No dominant order | Adjective-Noun | Noun-Relative clause |
| cy | 404 | 0.0149 | VSO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| ru | 6740 | 0.0147 | SVO | Prepositions | Noun-Genitive | Adjective-Noun | Noun-Relative clause |
| uk | 4266 | 0.0115 | SVO | Prepositions |  | Adjective-Noun | Noun-Relative clause |
| bs | 454 | 0.0110 |  |  |  |  |  |
| eo | 921 | 0.0109 |  |  |  |  |  |
| nl | 4811 | 0.0106 | No dominant order | Prepositions | Noun-Genitive | Adjective-Noun | Noun-Relative clause |
| ca | 2736 | 0.0106 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| fi | 2827 | 0.0103 | SVO | Postpositions | Genitive-Noun | Adjective-Noun | Noun-Relative clause |
| sr | 2100 | 0.0100 |  |  |  |  |  |
| gl | 1674 | 0.0096 |  |  |  |  |  |
| de | 8101 | 0.0094 | No dominant order | Prepositions | Noun-Genitive | Adjective-Noun | Noun-Relative clause |
| be | 1098 | 0.0091 | No dominant order |  | Noun-Genitive | Adjective-Noun | Noun-Relative clause |
| ga | 780 | 0.0090 | VSO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| fr | 7505 | 0.0089 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| pl | 5026 | 0.0088 | SVO | Prepositions | Noun-Genitive | Adjective-Noun | Noun-Relative clause |
| hr | 1561 | 0.0083 |  |  |  |  |  |
| fil | 631 | 0.0079 | VSO |  | Noun-Genitive | No dominant order | Noun-Relative clause |
| sl | 1444 | 0.0076 | SVO | Prepositions | No dominant order | Adjective-Noun |  |
| vi | 3185 | 0.0069 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| sw | 903 | 0.0066 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| el | 2651 | 0.0064 | No dominant order | Prepositions | Noun-Genitive | Adjective-Noun | Noun-Relative clause |
| ar | 4727 | 0.0063 | conflict | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| he | 2560 | 0.0051 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| ms | 675 | 0.0044 | conflict | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| th | 1374 | 0.0044 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| it | 6600 | 0.0042 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| mk | 533 | 0.0038 | SVO | Prepositions | No dominant order | Adjective-Noun |  |
| af | 599 | 0.0033 |  |  |  |  |  |
| sv | 3108 | 0.0032 | SVO | Prepositions | Genitive-Noun | Adjective-Noun | Noun-Relative clause |
| bg | 2005 | 0.0030 | SVO | Prepositions | No dominant order | Adjective-Noun | Noun-Relative clause |
| ro | 2584 | 0.0027 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| id | 3767 | 0.0027 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| es | 8523 | 0.0026 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| nn | 410 | 0.0024 |  |  |  |  |  |
| sq | 821 | 0.0024 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| is | 1284 | 0.0023 | SVO | Prepositions | Noun-Genitive | Adjective-Noun | Noun-Relative clause |
| pt | 9434 | 0.0021 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| lo | 576 | 0.0017 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| en | 1568 | 0.0013 | SVO | Prepositions | No dominant order | Adjective-Noun | Noun-Relative clause |
| nb | 2090 | 0.0010 |  |  |  |  |  |
| da | 2265 | 0.0009 | SVO | Prepositions | Genitive-Noun | Adjective-Noun | Noun-Relative clause |
| kab | 468 | 0.0000 | VSO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
| no | 706 | 0.0000 | SVO | Prepositions | No dominant order | Adjective-Noun | Noun-Relative clause |
| zu | 431 | 0.0000 | SVO | Prepositions | Noun-Genitive | Noun-Adjective | Noun-Relative clause |
