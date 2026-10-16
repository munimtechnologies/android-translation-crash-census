#!/usr/bin/env python3
"""Census 0.4.0: census 0.3.1 (census.py 0.3.0 + census_fixes.py) with the
argument types of a plural taken from every source quantity form.

getQuantityString passes every quantity the same arguments. Census 0.3.x
checked each translated form against the source form that reads the most
arguments and took the types from that form alone, so an argument the form
does not show was typed "any" and run as text. Jellyfin's
download_remove_description reads "%2$s" in [one] and "%1$d" in [other]; its
translated [other], [few] and [many] forms use %1$d, so 56 of them were
reported "crash-if-text" while the app passes an Int (downloads.size). Now an
argument's type is the first one any source form gives it; if two forms
disagree, the chosen form's own type stays, as before. The source form each
translation is run against is unchanged.

Every pair whose types change is written to plural_types.csv, with its
FormatCheck verdict under the old and the new types, and counted in
plural_types.json.

  python census_plurals.py --data-dir /data --out-dir /out   # same options as census.py

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import collections
import csv
import json
import os
import sys

import census
import census_fixes
import l10n_guard as g

__version__ = "0.4.0"

PLURAL_RULE = ("getQuantityString passes every quantity the same arguments, so each translated "
               "plural form is checked against the source form that reads the most of them, "
               "with each argument's type taken from any source form that shows it")
CHANGE_FIELDS = ["repo", "res", "locale", "key", "source_key", "types_before", "types",
                 "verdict_before", "verdict"]
CHANGES = []

_scan_tree_031 = census.scan_tree
_add_031 = census.Census.add
_write_031 = census.Census.write


def _kinds(specs):
    """{argument: kind}, the first kind other than "any" winning, as jvm_types."""
    kinds = {}
    for n, kind in specs or []:
        if kinds.get(n, "any") == "any":
            kinds[n] = kind
    return kinds


def plural_types(src_text, base, specs):
    """FormatCheck's argument letters for one plural: the chosen source form's
    specs, with arguments it leaves "any" (or doesn't show) typed by the other
    source forms, unless those forms disagree."""
    own = _kinds(specs)
    found = collections.defaultdict(set)
    for q in g._QUANTITIES:
        form = src_text.get("%s[%s]" % (base, q))
        if form is None:
            continue
        for n, kind in _kinds(g.java_formatted(g._android_text(form))).items():
            if kind != "any":
                found[n].add(kind)
    kinds = dict(own)
    for n, seen in found.items():
        if kinds.get(n, "any") == "any" and len(seen) == 1:
            kinds[n] = next(iter(seen))
    if not kinds:
        return census.jvm_types(specs)
    return ",".join(census.JVM_TYPES[kinds.get(i, "any")] for i in range(1, max(kinds) + 1))


def scan_tree(root):
    """census.scan_tree, with plural types from every source form."""
    pairs, stats = _scan_tree_031(root)
    sources = {}
    for p in pairs:
        q = g._QUANTITY_KEY_RE.match(p["key"])
        if not q:
            continue
        if p["res"] not in sources:
            strings, _, _ = census.read_resources(os.path.join(root, p["res"], "values"))
            sources[p["res"]] = {k: v[0] for k, v in strings.items()}
        types = plural_types(sources[p["res"]], q.group(1), g.java_formatted(p["source"]))
        if types != p["types"]:
            p["types_before"], p["types"] = p["types"], types
            stats["plural_types_changed"] += 1
    return pairs, stats


def add(self, repo, record, pairs, jvm):
    changed = [p for p in pairs if "types_before" in p]
    if changed:
        before = after = [None] * len(changed)
        if jvm is not None:
            before = jvm.check([(p["types_before"], p["source"], p["target"]) for p in changed])
            after = jvm.check([(p["types"], p["source"], p["target"]) for p in changed])
        for p, b, a in zip(changed, before, after):
            CHANGES.append({"repo": repo["web"], "res": p["res"], "locale": p["locale"],
                            "key": p["key"], "source_key": p["source_key"],
                            "types_before": p["types_before"], "types": p["types"],
                            "verdict_before": census.verdict(b)[0], "verdict": census.verdict(a)[0]})
    return _add_031(self, repo, record, pairs, jvm)


def write(self, meta):
    summary = _write_031(self, meta)
    rows = sorted(CHANGES, key=lambda r: (r["repo"], r["locale"], r["key"]))
    with open(os.path.join(self.out_dir, "plural_types.csv"), "w", encoding="utf-8",
              errors="replace", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CHANGE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    moves = collections.Counter("%s -> %s" % (r["verdict_before"], r["verdict"]) for r in rows)
    by_repo = collections.Counter(r["repo"] for r in rows
                                  if r["verdict_before"] != r["verdict"])
    with open(os.path.join(self.out_dir, "plural_types.json"), "w", encoding="utf-8") as f:
        json.dump({"census_version": __version__, "pairs_with_new_types": len(rows),
                   "verdict_moves": dict(moves.most_common()),
                   "repos_with_verdict_moves": dict(by_repo.most_common())},
                  f, ensure_ascii=False, indent=1)
    return summary


def apply():
    """Points census.py at the 0.3.1 fixes and these. Safe to call twice."""
    census_fixes.apply()
    census.scan_tree = scan_tree
    census.Census.add = add
    census.Census.write = write
    census.PLURAL_RULE = PLURAL_RULE
    census.__version__ = __version__
    census.USER_AGENT = ("mv2-translation-crash-census/%s (Munim, Inc.; munimversion2@gmail.com)"
                         % __version__)


if __name__ == "__main__":
    apply()
    sys.exit(census.main())
