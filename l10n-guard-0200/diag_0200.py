# Diagnosis of l10n-guard 0.20.0's R4 miss (exploratory, not a pre-registered test).
# In the 0.20.0 check, three orphans that 0.19.0 reported and the hand check called real
# (Clock th and ca, mighty-alarm-clock ja) were no longer reported. This script reads the two
# repositories at the checked commits and prints, per translation folder, the count 0.19.0 used
# (strings present), the count 0.20.0 uses (strings that differ, plus copies of one-word or
# wordless defaults), the module's default total and the 50% line, and the strings 0.20.0 drops.
# The counting functions are copied from l10n-guard 0.20.0 (_lc_strings, _lc_count).
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

CASES = [
    ("https://github.com/BlackyHawky/Clock", "4899ab538d18e2453dcbaeff9d435689295a2a08"),
    ("https://github.com/RapidAppCoder/mighty-alarm-clock", "f105cb4997659f7bb3a6f4e4842e10981afc83dc"),
]
SKIP = frozenset(["build", "test", "androidTest", "testFixtures", "sharedTest"])
DIR_RE = re.compile(r"^values-(?:([a-z]{2,3})(?:-r[A-Z]{2})?|b\+([a-z]{2,3})(?:\+[A-Za-z0-9]+)*)$")
LETTERS2_RE = re.compile(r"[^\W\d_]{2,}")


def lc_strings(data, default):
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError):
        return None
    out = {}
    if root.tag != "resources":
        return out
    for e in root:
        if e.tag not in ("string", "plurals", "string-array"):
            continue
        name = e.get("name")
        if not name or (default and e.get("translatable") == "false"):
            continue
        text = " ".join("".join(e.itertext()).split())
        if not default and not text:
            continue
        out[name] = text
    return out


def lc_count(tr, base):
    counted = differ = 0
    dropped = []
    for name, text in tr.items():
        if name not in base:
            continue
        if text != base[name]:
            differ += 1
            counted += 1
        elif len(base[name].split()) <= 1 or not LETTERS2_RE.search(base[name]):
            counted += 1
        else:
            dropped.append((name, text))
    return counted, differ, dropped


def module(path):
    parts = path.split("/")
    head = parts[:-1]
    if "src" in head:
        i = len(head) - 1 - head[::-1].index("src")
        return "/".join(parts[:i])
    return "/".join(head)


def git(args, cwd=None):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900)


def read_repo(url, commit, tmp):
    s = os.path.join(tmp, "s")
    git(["init", "--quiet", s])
    git(["-C", s, "remote", "add", "origin", url])
    r = git(["-C", s, "fetch", "--quiet", "--depth", "1", "--filter=blob:none", "origin", commit])
    if r.returncode != 0:
        raise RuntimeError("fetch failed: " + r.stderr.strip()[-300:])
    git(["-C", s, "config", "core.sparseCheckout", "true"])
    git(["-C", s, "config", "core.sparseCheckoutCone", "false"])
    with open(os.path.join(s, ".git", "info", "sparse-checkout"), "w", encoding="utf-8") as fh:
        fh.write("**/values/*.xml\n**/values-*/*.xml\n")
    co = git(["-C", s, "checkout", "--quiet", commit])
    if co.returncode != 0:
        raise RuntimeError("checkout failed: " + co.stderr.strip()[-300:])
    lt = git(["-C", s, "ls-tree", "-r", "-z", "--name-only", commit])
    paths = [p for p in lt.stdout.split("\0") if p]
    return s, paths


def analyse(url, commit):
    tmp = tempfile.mkdtemp()
    try:
        s, paths = read_repo(url, commit, tmp)
        files = {}
        for p in paths:
            parts = p.split("/")
            if len(parts) < 3 or parts[-3] != "res" or not parts[-1].endswith(".xml"):
                continue
            if any(x in SKIP or x.startswith(".") for x in parts[:-1]):
                continue
            if parts[-2] != "values" and not parts[-2].startswith("values-"):
                continue
            files.setdefault(("/".join(parts[:-2]), parts[-2]), set()).add(parts[-1])

        def strings(res_dir, d, fn, default):
            fp = os.path.join(s, res_dir, d, fn)
            if not os.path.isfile(fp):
                return {}
            with open(fp, "rb") as fh:
                return lc_strings(fh.read(), default) or {}

        mods = {}
        for (res_dir, d), names in sorted(files.items()):
            mod = module(res_dir + "/x")
            m = mods.setdefault(mod, {"res_dirs": {}, "den": 0, "folders": {}})
            if d == "values":
                n = {fn: len(strings(res_dir, d, fn, True)) for fn in sorted(names)}
                m["res_dirs"][res_dir] = n
                m["den"] += sum(n.values())
        for (res_dir, d), names in sorted(files.items()):
            if d == "values":
                continue
            mm = DIR_RE.match(d)
            if not mm:
                continue
            mod = module(res_dir + "/x")
            m = mods[mod]
            default_names = files.get((res_dir, "values"), set())
            shared = sorted(names & default_names)
            if not shared:
                continue
            n19 = n20 = differ = 0
            dropped = []
            for fn in shared:
                tr = strings(res_dir, d, fn, False)
                base = strings(res_dir, "values", fn, True)
                n19 += len(set(tr) & set(base))
                c, df, dr = lc_count(tr, base)
                n20 += c
                differ += df
                dropped += [{"file": fn, "name": a, "text": b[:160]} for a, b in dr]
            f = m["folders"].setdefault(d, {"n19": 0, "n20": 0, "differ": 0, "dropped": []})
            f["n19"] += n19
            f["n20"] += n20
            f["differ"] += differ
            f["dropped"] += dropped
        out = {"repo": url, "commit": commit, "modules": {}}
        for mod, m in sorted(mods.items()):
            den = m["den"]
            folders = {}
            for d, f in sorted(m["folders"].items()):
                folders[d] = {"n19": f["n19"], "n20": f["n20"], "differ": f["differ"],
                              "orphan_size_0190": bool(den) and 2 * f["n19"] >= den,
                              "orphan_size_0200": bool(den) and 2 * f["n20"] >= den,
                              "dropped_count": len(f["dropped"]),
                              "dropped_first": f["dropped"][:25]}
            out["modules"][mod or "."] = {"den": den, "default_files": m["res_dirs"],
                                         "folders": folders}
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for url, commit in CASES:
        try:
            r = analyse(url, commit)
        except Exception as exc:
            r = {"repo": url, "commit": commit, "error": repr(exc)[:300]}
        results.append(r)
        for mod, m in r.get("modules", {}).items():
            for d, f in m["folders"].items():
                if f["orphan_size_0190"] != f["orphan_size_0200"]:
                    print("%s %s %s: den %d, n19 %d, n20 %d, differ %d, dropped %d" % (
                        url, mod, d, m["den"], f["n19"], f["n20"], f["differ"],
                        f["dropped_count"]), flush=True)
    with open(os.path.join(out_dir, "diag.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return 0 if all("error" not in r for r in results) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "out"))
