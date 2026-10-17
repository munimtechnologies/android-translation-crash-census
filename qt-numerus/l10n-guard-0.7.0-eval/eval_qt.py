#!/usr/bin/env python3
"""Runs the Qt check of a patched l10n_guard.py on real .ts files: the files
where a plural count written ٪n or ％n was found by hand on 2026-10-17, and a
few unaffected ones from the same projects as a control. Records, per file,
the commit read, the message counts and every issue by code.

  python eval_qt.py --guard /out/l10n_guard.py --out-dir /out/eval

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import sys
import urllib.request

# (repository, path, what was seen by hand)
FILES = [
    ("bitcoin/bitcoin", "src/qt/locale/bitcoin_ar.ts", "٪n in plural forms (49 lines)"),
    ("bitcoin/bitcoin", "src/qt/locale/bitcoin_zh_TW.ts", "％n in a plural form (1 line)"),
    ("bitcoin/bitcoin", "src/qt/locale/bitcoin_zh-Hant.ts", "％n in a plural form (1 line)"),
    ("bitcoin/bitcoin", "src/qt/locale/bitcoin_de.ts", "control"),
    ("keepassxreboot/keepassxc", "share/translations/keepassxc_ar.ts", "٪n in plural forms (30 lines)"),
    ("keepassxreboot/keepassxc", "share/translations/keepassxc_de.ts", "control"),
    ("pbek/QOwnNotes", "src/languages/QOwnNotes_ur.ts", "٪n (4 lines)"),
    ("pbek/QOwnNotes", "src/languages/QOwnNotes_ja.ts", "％n (6 lines)"),
    ("OtterBrowser/otter-browser", "resources/translations/otter-browser_ja.ts", "％n (3 lines)"),
    ("OpenOrienteering/mapper", "translations/OpenOrienteering_zh_CN.ts", "％n (2 lines)"),
]
UA = {"User-Agent": "mv2-l10n-guard-eval"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def head_commit(repo):
    try:
        data = json.loads(get("https://api.github.com/repos/%s/commits/HEAD" % repo).decode("utf-8"))
        return data.get("sha", "")
    except Exception as exc:  # the commit is a record, not a requirement
        return "unknown (%s)" % type(exc).__name__


def load_guard(path):
    spec = importlib.util.spec_from_file_location("l10n_guard", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard", default="/out/l10n_guard.py")
    parser.add_argument("--out-dir", default="/out/eval")
    args = parser.parse_args()
    g = load_guard(args.guard)
    os.makedirs(args.out_dir, exist_ok=True)
    results, md = [], ["# l10n-guard %s Qt check on real .ts files" % g.__version__, "",
                       "| repository | file | seen by hand | commit | messages | finished | issues by code |",
                       "|---|---|---|---|---:|---:|---|"]
    details = []
    commits = {}
    for repo, path, seen in FILES:
        if repo not in commits:
            commits[repo] = head_commit(repo)
        commit = commits[repo]
        ref = commit if len(commit) == 40 else "HEAD"
        row = {"repo": repo, "path": path, "seen": seen, "commit": commit}
        try:
            data = get("https://raw.githubusercontent.com/%s/%s/%s" % (repo, ref, path))
            row["sha256"] = hashlib.sha256(data).hexdigest()
            text = data.decode("utf-8-sig").replace("\r\n", "\n")
            problems, stats = g.check_qt(text)
        except Exception as exc:
            row["error"] = "%s: %s" % (type(exc).__name__, exc)
            results.append(row)
            md.append("| %s | %s | %s | %s | - | - | %s |" % (repo, path, seen, commit[:10], row["error"][:80]))
            print("%s %s: %s" % (repo, path, row["error"]), flush=True)
            continue
        by_code = collections.Counter("%s/%s" % (p["code"], p["level"]) for p in problems)
        row.update(stats=stats, by_code=dict(sorted(by_code.items())), issues=problems)
        results.append(row)
        md.append("| %s | %s | %s | %s | %d | %d | %s |" % (
            repo, path, seen, commit[:10], stats["messages"], stats["finished"],
            ", ".join("%s %d" % kv for kv in sorted(by_code.items())) or "none"))
        counts = [p for p in problems if p["code"].startswith("qt-count")]
        if counts:
            details += ["", "## %s %s" % (repo, path), ""]
            details += ["- %s [%s]: %s" % (p["level"].upper(), p.get("key", ""), p["message"]) for p in counts]
        print("%s %s: %d messages, %s" % (repo, path, stats["messages"], json.dumps(row["by_code"])), flush=True)
    with open(os.path.join(args.out_dir, "eval_qt.json"), "w", encoding="utf-8") as f:
        json.dump({"version": g.__version__, "files": results}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out_dir, "eval_qt.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md + ["", "Plural-count issues, in full:"] + details) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
