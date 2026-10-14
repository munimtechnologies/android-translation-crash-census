# What kind of mistake breaks each crashing translation

taxonomy.py 0.1.1 (MV2 of Munim, Inc., made with AI agents).

## all-crash: 382 rows in 99 repositories

| kind | rows | repositories | top languages |
|---|---:|---:|---|
| stray-percent | 82 | 41 | ar 10, zh 5, zh-rCN 4, fa-rIR 4, ru 4, sl 4, iw 3, ckb 3 |
| malformed-index | 65 | 11 | ug 52, az 2, eu 2, ga 1, ru 1, es 1, sv 1, pl 1 |
| conversion-missing | 66 | 26 | sr 7, el 6, ckb 5, sq-rAL 4, pl 4, ka 4, tcy 4, sv 3 |
| conversion-native | 28 | 8 | ru 6, bg 5, ar 3, pa 3, uk 3, el 2, zh 2, iw-rIL 1 |
| conversion-invalid | 10 | 7 | eu 3, oc 2, la 2, tr 2, he 1 |
| flag-mismatch | 52 | 22 | tr 25, es 5, lt 3, fr 2, kmr 2, ug 2, da 1, bg 1 |
| argument-not-passed | 59 | 20 | hu 6, ko 6, qq 5, uk 4, ru 4, bn-rBD 3, bn-rIN 3, eu 3 |
| wrong-type | 20 | 10 | bn 3, is 3, vi 3, it 2, eu 2, de 1, la 1, fr 1 |

Scripts of the letters right after an indexed placeholder: CYRILLIC 15, ARABIC 3, GURMUKHI 3, GREEK 2, CJK 2, HEBREW 1, BENGALI 1, KANNADA 1
15 of them look like or transliterate a Latin conversion letter (Cyrillic с for s, Greek δ for d...).

## formatted-crash: 250 rows in 67 repositories

| kind | rows | repositories | top languages |
|---|---:|---:|---|
| stray-percent | 45 | 26 | ar 6, zh-rCN 3, fa-rIR 3, sl 3, it 2, be-rBY 2, el 2, ja 2 |
| malformed-index | 50 | 5 | ug 44, eu 2, sv 1, pl 1, af 1, th 1 |
| conversion-missing | 43 | 18 | sr 7, sq-rAL 4, ckb 4, pl 3, sv 3, ar 3, ka 3, gu 3 |
| conversion-native | 26 | 6 | ru 6, bg 5, ar 3, pa 3, uk 3, el 2, zh 2, bn 1 |
| conversion-invalid | 7 | 4 | oc 2, la 2, tr 2, he 1 |
| flag-mismatch | 34 | 14 | tr 22, lt 2, da 1, es 1, fr 1, cs 1, sl 1, nl 1 |
| argument-not-passed | 35 | 15 | ko 6, uk 4, ru 4, it 3, pt 2, pt-rBR 2, in-rID 2, da 2 |
| wrong-type | 10 | 5 | is 3, vi 3, la 1, fr 1, br 1, cs-rCZ 1 |

Scripts of the letters right after an indexed placeholder: CYRILLIC 14, ARABIC 3, GURMUKHI 3, GREEK 2, CJK 2, BENGALI 1, KANNADA 1
14 of them look like or transliterate a Latin conversion letter (Cyrillic с for s, Greek δ for d...).

## Examples (formatted strings)

- **conversion-invalid**: Briar oc `You have invited %1$s to join the group "%2$s".` -> `Avètz convidat %1$s a venir al grop « %2$vs»`; Andor's Trail la `You picked up %1$,d items.` -> `%1$D items sustulistis.`; Anonomi Messenger oc `You have invited %1$s to join the group "%2$s".` -> `Avètz convidat %1$s a venir al grop « %2$vs»`; Cashiro he `%1$dh %2$dm` -> `%1$DH %2$DM`
- **argument-not-passed**: Bimba uk `%1$s grafuts` -> `%1$s %2$s графути`; Bimba uk `%1$s grafuts` -> `%1$s %2$s графутів`; Bimba uk `%1$s grafuts` -> `%1$s %2$s графут`; Bimba uk `%1$s grafuts` -> `%1$s %2$s графутів`
- **flag-mismatch**: Who Has My Stuff? da `Expecting the return of %1$s from %2$s` -> `Forventes afkastet på %1$ s fra %2$s`; MoneyWallet tr `Hi, take a look at %s` -> `Merhaba,% s bölümüne bir göz atın`; MoneyWallet tr `Failure during the creation of the backup. Message: %s` -> `Yedeklemenin oluşturulması sırasında hata oluştu. Mesaj:% s`; MoneyWallet tr `Failure during the restoring of the backup. Message: %s` -> `Yedeklemenin geri yüklenmesi sırasında hata oluştu. Mesaj:% s`
- **stray-percent**: spaRSS DecSync ar `%d new entries` -> `d% مقالات جديدة`; spaRSS DecSync ar `%d new entries` -> `d% مقالات جديدة`; spaRSS DecSync ar `%d new entries` -> `d% مقالة جديدة`; Flashy fr `Farnsworth timing makes recognizing the sound patterns easier by increasing the gaps between the characters and words to give more recognition time.
A Farnsworth unit is longer than a basic unit.
Enter your desired length of a Farnsworth unit below (must be longer than a basic unit: %d milliseconds).
Leave blank to use the length of the basic unit plus an additional 25 percent of it.` -> `La méthode Farnsworth permet de reconnaître les motifs sonores plus facilement en augmentant le délai entre les lettres et entre les mots, ce qui laisse plus de temps pour les identifier. 
Une unité Farnsworth est plus longue qu'une unité de base. 
Écrivez ci-contre la longueur voulue pour votre unité Farnsworth (plus longue qu'une unité de base : %d millisecondes). 
Laissez vide pour utiliser la longueur d'une unité de base augmentée de 25%.`
- **wrong-type**: Andor's Trail la `Enables critical hits with a multiplier of x%1$.1f` -> `Hits critica ope multiplicatoris ex x %1$,d.1f *`; Baby Name fr `%s rated: %.1f` -> `%s noté: %d`; OsmAnd~ br `%1$s ago` -> `%1$e 'zo`; Cashiro is `%1$dh %2$dm` -> `%1$dt %2$tm`
- **conversion-missing**: Moshidon sq-rAL `%d people are talking` -> `Po flet %1 person`; Moshidon sq-rAL `%d people are talking` -> `Po flasin %1 persona`; Iris Gallery pl `%1$d Videos` -> `Wideo (%1)`; RootlessJamesDSP ko-rKR `New update available (%1$s)` -> `새 업데이트 사용 가능 (%1&s)`
- **malformed-index**: Pedometer (PFA) sv `%1$.2f %2$s walked today.` -> `%1 $ .2f %2$s gått idag.`; Rethink: DNS + Firewall + VPN pl `On-device blocklists are already at the latest version v%1$s.` -> `Listy blokowania na urządzeniu są już w najnowszej wersji v% 1$s.`; Commons af `Uploaded by: %1$s` -> `Opgelaai deur:%$1s`; Commons th `No categories matching %1$s found` -> `ไม่พบหมวดหมู่ที่ตรงกับ %$1s`
- **conversion-native**: FadCam el `ETA %1$dm %2$02ds` -> `Εκτ. %1$δλ %2$02δδ`; FadCam el `ETA %1$ds` -> `Εκτ. %1$δδ`; Commons zh `Nominated %1$s for deletion.` -> `已提出将%1删除`; Commons zh `No Wikidata items matching %1$s found` -> `未找到符合%1$的维基数据项目。`
