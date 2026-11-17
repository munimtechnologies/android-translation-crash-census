# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents by MV2 of Munim, Inc.
"""Grade the Starlight script-tag build against PREREG.md. Always exits 0.

Usage: python3 check.py <site dir> <out dir>
"""
import html
import json
import os
import re
import sys

KEYS = ["skipLink.label", "search.label", "themeSelect.accessibleLabel",
        "tableOfContents.onThisPage"]

# Used only if the installed package's own translation files cannot be found.
def _u(*cps):
    return "".join(chr(c) for c in cps)


FALLBACK = {
    "en": ["Skip to content", "Search", "Select theme", "On this page"],
    "zh": [_u(0x8DF3, 0x8F6C, 0x5230, 0x5185, 0x5BB9), _u(0x641C, 0x7D22),
           _u(0x9009, 0x62E9, 0x4E3B, 0x9898), _u(0x672C, 0x9875, 0x5185, 0x5BB9)],
    "zh-TW": [_u(0x8DF3, 0x5230, 0x5167, 0x5BB9), _u(0x641C, 0x5C0B),
              _u(0x9078, 0x64C7, 0x4F48, 0x666F, 0x4E3B, 0x984C),
              _u(0x672C, 0x9801, 0x5167, 0x5BB9)],
    "es": ["Ir al contenido", "Buscar", "Seleccionar tema", "En esta p" + _u(0xE1) + "gina"],
}
DICT_FILES = {"en": "en.json", "zh": "zh-CN.json", "zh-TW": "zh-TW.json", "es": "es.json"}

# folder -> (lang, expected dictionary, prediction id)
EXPECT = [
    ("", "en", "en", "C0"),
    ("zh-tw", "zh-TW", "zh-TW", "C1"),
    ("zh-cn", "zh-CN", "zh", "C2"),
    ("es-mx", "es-MX", "es", "C3"),
    ("zh-hant", "zh-Hant", "en", "P1"),
    ("zh-hans", "zh-Hans", "en", "P2"),
    ("zh-hk", "zh-HK", "zh", "P3"),
    ("es-419", "es-419", "en", "P4"),
    ("zh-hant-tw", "zh-Hant-TW", "en", "P5"),
]

REGEX_TEXT = "/-[a-zA-Z]{2}/"


def find_pkg(site):
    return os.path.join(site, "node_modules", "@astrojs", "starlight")


def load_dicts(pkg):
    """Return (dicts, source, found_dir)."""
    found = None
    for root, dirs, files in os.walk(pkg):
        if "node_modules" in root[len(pkg):]:
            continue
        if os.path.basename(root) == "translations" and "en.json" in files \
                and "zh-TW.json" in files:
            found = root
            break
    if not found:
        return FALLBACK, "hard-coded", None
    out = {}
    for name, fn in DICT_FILES.items():
        try:
            with open(os.path.join(found, fn), encoding="utf-8") as f:
                d = json.load(f)
            vals = [d.get(k) for k in KEYS]
            if any(v is None for v in vals):
                return FALLBACK, "hard-coded (key missing in %s)" % fn, found
            out[name] = vals
        except Exception as e:  # noqa: BLE001
            return FALLBACK, "hard-coded (%s: %s)" % (fn, e), found
    return out, "package", found


def source_check(pkg):
    hits = []
    for root, dirs, files in os.walk(pkg):
        if "node_modules" in root[len(pkg):]:
            continue
        for fn in files:
            if fn.startswith("createTranslationSystem"):
                p = os.path.join(root, fn)
                try:
                    with open(p, encoding="utf-8", errors="replace") as f:
                        txt = f.read()
                except OSError:
                    continue
                m = re.search(r"function stripLangRegion[^}]*}", txt)
                hits.append({"file": os.path.relpath(p, pkg),
                             "has_regex": REGEX_TEXT in txt,
                             "stripLangRegion": m.group(0) if m else None})
    return hits


def classify(page, dicts):
    counts = {}
    for name, vals in dicts.items():
        counts[name] = sum(1 for v in vals if v and v in page)
    best = max(counts.values()) if counts else 0
    tops = [n for n, c in counts.items() if c == best]
    if best >= 3 and len(tops) == 1:
        return tops[0], counts
    return "unclear", counts


def html_lang(raw):
    m = re.search(r"<html[^>]*\blang=\"([^\"]*)\"", raw)
    return m.group(1) if m else None


def version_of(site, name):
    p = os.path.join(site, "node_modules", *name.split("/"), "package.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f).get("version")
    except Exception:  # noqa: BLE001
        return None


def main(site, out):
    os.makedirs(out, exist_ok=True)
    res = {"versions": {n: version_of(site, n) for n in
                        ("astro", "@astrojs/starlight", "i18next")}}
    try:
        with open(os.path.join(out, "build_exit.txt"), encoding="utf-8") as f:
            res["build_exit"] = f.read().strip()
    except OSError:
        res["build_exit"] = None
    warnings = []
    try:
        with open(os.path.join(out, "build.log"), encoding="utf-8", errors="replace") as f:
            for line in f:
                low = line.lower()
                if "warn" in low or "error" in low or "language tag" in low:
                    warnings.append(line.rstrip()[:300])
    except OSError:
        pass
    res["build_warnings"] = warnings[:60]
    pkg = find_pkg(site)
    dicts, src, ddir = load_dicts(pkg)
    res["dict_source"] = src
    res["dict_dir"] = os.path.relpath(ddir, site) if ddir else None
    res["dict_values"] = dicts
    res["source_check"] = source_check(pkg)
    pages = []
    verdicts = {}
    for folder, lang, want, pid in EXPECT:
        p = os.path.join(site, "dist", folder, "index.html") if folder else \
            os.path.join(site, "dist", "index.html")
        row = {"id": pid, "folder": folder or "(root)", "lang": lang, "expected": want}
        if not os.path.exists(p):
            row.update({"exists": False, "got": None, "holds": False})
        else:
            with open(p, encoding="utf-8", errors="replace") as f:
                raw = f.read()
            got, counts = classify(html.unescape(raw), dicts)
            row.update({"exists": True, "html_lang": html_lang(raw), "got": got,
                        "counts": counts, "holds": got == want})
        pages.append(row)
        verdicts[pid] = row["holds"]
    res["pages"] = pages
    verdicts["B"] = res["build_exit"] == "0"
    sc = res["source_check"]
    verdicts["S"] = bool(sc) and all(h["has_regex"] for h in sc)
    controls = all(verdicts[k] for k in ("B", "C0", "C1", "C2", "C3"))
    verdicts["controls_hold"] = controls
    verdicts["H"] = controls and verdicts["P1"] and verdicts["P3"] and verdicts["P4"]
    res["verdicts"] = verdicts
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(json.dumps(verdicts))
    for row in pages:
        print(row["id"], row["lang"], "expected", row["expected"], "got", row.get("got"),
              row.get("counts"), "html lang", row.get("html_lang"))
    return 0


if __name__ == "__main__":
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:  # noqa: BLE001
        print("check.py error:", repr(e))
    sys.exit(0)
