#!/usr/bin/env python3
"""Checks census 0.4.0's findings.csv against rows read by hand
(data/crash-if-text-audit.csv, 2026-10-16): Jellyfin's 56
download_remove_description "crash-if-text" rows must be gone, Jellyfin's
Swedish [one] form (a real stray "%1" before a quote) must stay a crash, and
the plural crashes the audit confirmed must still be reported. Writes
check.md; exits 1 on a miss.

  python check_findings.py /out/findings.csv --out /out/check.md

0.1.1: the Jellyfin check counts only "crash-if-text" rows. 0.1.0 also
counted the Swedish crash, which a hand reading confirmed (data/v6/NOTES.md).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import sys

__version__ = "0.1.1"

# (repo, locale, key, expected, verdict): expected is "gone" or "reported";
# verdict, when set, counts only rows with that verdict.
EXPECTED = [
    ("jellyfin/jellyfin-android", None, "download_remove_description[", "gone", "crash-if-text"),
    ("jellyfin/jellyfin-android", "sv", "download_remove_description[one]", "reported", "crash"),
    ("session-foundation/session-android", "b+si+LK", "emojiReactsCountOthers[one]", "reported", None),
    ("session-foundation/session-android", "b+si+LK", "emojiReactsCountOthers[other]", "reported", None),
    ("rascarlo/AURdroid", "es", "plurals_formatted_package_found[one]", "reported", None),
    ("rascarlo/AURdroid", "es", "plurals_formatted_package_found[other]", "reported", None),
    ("d4rken-org/sdmaid-se", "ka-rGE", "corpsefinder_watcher_notification_delete_result[one]",
     "reported", None),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("findings")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    with open(args.findings, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    lines = ["# census 0.4.0 checks against the hand audit", "",
             "check_findings.py %s, %d rows read." % (__version__, len(rows)), "",
             "| repo | locale | key | expected | verdict counted | rows found | verdicts | result |",
             "|---|---|---|---|---|---|---|---|"]
    misses = 0
    for repo, locale, key, expected, verdict in EXPECTED:
        hits = [r for r in rows if r["repo"].lower().endswith("/" + repo.lower())
                and (locale is None or r["locale"] == locale)
                and (r["key"].startswith(key) if key.endswith("[") else r["key"] == key)
                and (verdict is None or r["verdict"] == verdict)]
        ok = (not hits) if expected == "gone" else bool(hits)
        misses += 0 if ok else 1
        verdicts = ", ".join(sorted({r["verdict"] for r in hits})) or "-"
        lines.append("| %s | %s | %s | %s | %s | %d | %s | %s |" % (
            repo, locale or "all", key, expected, verdict or "any", len(hits), verdicts,
            "ok" if ok else "MISS"))
    lines += ["", "%d of %d checks passed." % (len(EXPECTED) - misses, len(EXPECTED))]
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
