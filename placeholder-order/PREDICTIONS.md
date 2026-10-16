# placeholder-order 0.1.0: predictions written before the run

MV2 of Munim, Inc. Made with AI agents. Written 2026-10-16 ~17:45Z, before job placeholder-order-v1 ran.
placeholder_order.py checks each one itself and writes HELD / FAILED into report.md and summary.json.

Question: when an English Android string has two or more format arguments, how often does a translation
put them in a different order, per language, and how often is that done unsafely (moving unnumbered
placeholders, which Java fills left to right) instead of with numbers (%2$s)?

Prior art (searched 2026-10-16): style guides (Django, Microsoft, WebTranslateIt, Smartling) say translators
need to reorder and recommend numbered placeholders; a cmux PR (manaflow-ai/cmux#16376) fixed a checker that
rejected a valid Japanese reorder. No measurement of how often it happens, by language, was found.

Data: the same F-Droid repositories and string pairs as android-translation-crash-census 0.3.1 (F-Droid
index cached in the census's data volume), plural forms left out.

- P1. For sources with unnumbered placeholders of mixed kinds (%s with %d), the pooled reorder rate of
  SOV languages (Japanese, Korean, Turkish, Hindi, ...) is at least twice that of SVO languages.
- P2. The same holds for numbered sources (%1$s ... %2$s), where reordering is free.
- P3. Japanese and Korean are both in the top 5 languages (20+ repositories) by numbered-source reorder rate.
- P4. At least 10% of the reorders of mixed-kind unnumbered sources move unnumbered placeholders (unsafe).
- P5. In both SOV and SVO groups, numbered sources are reordered more often than mixed-kind unnumbered ones
  (numbers in the source free translators to reorder).
- P6. On unnumbered sources, translations that add numbers but keep the source order outnumber numbered
  reorders (translators number defensively).

Not predicted, reported as found: the per-language table, the effect of repeated strings (repo mean and
unique-pair columns), and the list of unsafe reorders (unnumbered_reordered.csv), which feeds the audit.
