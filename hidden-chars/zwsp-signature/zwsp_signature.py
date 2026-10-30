"""How stray zero-width spaces sit in shipped Android translations (hidden-chars follow-up).

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents. Apache-2.0.

Exploratory, NOT pre-registered: rough counts that prompted it were seen first. It reads the
published hidden-chars/hits.csv and, for every row whose only extra character is U+200B,
classifies each run of U+200B by its length and neighbours. The pattern of interest is a run of
exactly two U+200B after an ordinary space and before a letter ("pair-after-space"), the shape
reported in Google Translate API output ("il <U+200B><U+200B>rilascio") in a developer thread on
the google-translate-api Google Group.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import re
import sys
import urllib.request

__version__ = "0.1.0"

HITS_URL = ("https://raw.githubusercontent.com/munimtechnologies/"
            "android-translation-crash-census/main/hidden-chars/hits.csv")
ZWSP = chr(0x200B)
MARK_RE = re.compile(r"<U\+([0-9A-F]{4,6})>")
KIND_ORDER = ("pair-after-space", "pair-other", "longer", "single")


def decode(text):
    """Turn hits.csv markers like <U+200B> back into the characters."""
    return MARK_RE.sub(lambda m: chr(int(m.group(1), 16)), text)


def runs(text):
    """Return (length, before, after) for each run of U+200B; '' at the string edges."""
    out = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != ZWSP:
            i += 1
            continue
        j = i
        while j < n and text[j] == ZWSP:
            j += 1
        out.append((j - i, text[i - 1] if i else "", text[j] if j < n else ""))
        i = j
    return out


def kind(run):
    length, before, after = run
    if length == 2 and before == " " and after.isalpha():
        return "pair-after-space"
    if length == 2:
        return "pair-other"
    if length == 1:
        return "single"
    return "longer"


def classify(target):
    """One kind per row, the first in KIND_ORDER that any of its runs has."""
    kinds = {kind(r) for r in runs(decode(target))}
    for k in KIND_ORDER:
        if k in kinds:
            return k
    return "none"


def analyze(rows):
    total = 0
    by_kind = collections.Counter()
    by_platform = collections.defaultdict(collections.Counter)
    zwsp_repo = collections.Counter()
    sig_repo = collections.Counter()
    sig_lang = collections.Counter()
    sig_keys = collections.defaultdict(set)
    examples = []
    for row in rows:
        if row["classes"] != "zwsp" or row["codepoints"] != "U+200B":
            continue
        total += 1
        k = classify(row["target"])
        by_kind[k] += 1
        by_platform[row["platform"]][k] += 1
        zwsp_repo[row["repo"]] += 1
        if k != "pair-after-space":
            continue
        sig_repo[row["repo"]] += 1
        sig_lang[row["lang"]] += 1
        sig_keys[(row["repo"], row["key"])].add(row["lang"])
        if len(examples) < 40:
            examples.append({"repo": row["repo"], "lang": row["lang"], "key": row["key"],
                             "target": row["target"][:160]})
    shared = sorted(((repo, key, sorted(langs)) for (repo, key), langs in sig_keys.items()
                     if len(langs) >= 3), key=lambda t: (-len(t[2]), t[0], t[1]))
    sig = by_kind["pair-after-space"]
    top = sig_repo.most_common()
    return {
        "zwsp_only_rows": total,
        "by_kind": dict(sorted(by_kind.items())),
        "signature_rows": sig,
        "signature_share": round(sig / total, 4) if total else None,
        "by_platform": {p: dict(sorted(c.items())) for p, c in sorted(by_platform.items())},
        "repos_with_zwsp": len(zwsp_repo),
        "repos_with_signature": len(sig_repo),
        "langs_with_signature": len(sig_lang),
        "signature_rows_in_top_repo": top[0][1] if top else 0,
        "signature_rows_in_top5_repos": sum(c for _, c in top[:5]),
        "top_repos": [[r, c, zwsp_repo[r]] for r, c in top[:15]],
        "top_langs": [[l, c] for l, c in sig_lang.most_common(20)],
        "shared_keys_3plus_langs": len(shared),
        "shared_keys": [[r, k, ";".join(ls)] for r, k, ls in shared],
        "repo_counts": [[r, sig_repo[r], c] for r, c in sorted(zwsp_repo.items())],
        "lang_counts": sorted([l, c] for l, c in sig_lang.items()),
        "examples": examples,
    }


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--hits", default="", help="local hits.csv; downloaded if missing")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    path = args.hits or os.path.join(args.out_dir, "hits.csv")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if not os.path.exists(path):
        with urllib.request.urlopen(HITS_URL, timeout=180) as r, open(path, "wb") as f:
            f.write(r.read())
    with open(path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    csv.field_size_limit(10 ** 7)
    with open(path, encoding="utf-8", newline="") as f:
        result = analyze(csv.DictReader(f))
    os.makedirs(args.out_dir, exist_ok=True)
    write_csv(os.path.join(args.out_dir, "by_repo.csv"), ["repo", "signature_rows", "zwsp_only_rows"],
              result.pop("repo_counts"))
    write_csv(os.path.join(args.out_dir, "by_lang.csv"), ["lang", "signature_rows"],
              result.pop("lang_counts"))
    write_csv(os.path.join(args.out_dir, "shared_keys.csv"), ["repo", "key", "langs"],
              result["shared_keys"])
    result.update({"version": __version__, "hits_sha256": sha, "hits_url": HITS_URL})
    with open(os.path.join(args.out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: result[k] for k in ("zwsp_only_rows", "by_kind", "signature_share",
                                             "repos_with_signature", "langs_with_signature")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
