#!/usr/bin/env python3
# vitepress_locales: translated folders that a VitePress site serves under the wrong language.
# Standard library only, no network. Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
"""Check a VitePress site for translation folders that its `locales` config does not match.

What VitePress does (read in vuejs/vitepress at commit 40b2e09, version 2.0.0-alpha.21; this is
source reading, not a build test):
- src/node/plugins/dynamicRoutesPlugin.ts, resolvePages(): every **/*.md file under srcDir is a
  page. Only the user's srcExclude filters the list; the locales config is not consulted.
- src/shared/shared.ts, getLocaleForPath(): a page belongs to the first key of `locales` (other
  than root) for which new RegExp(`^/${key}/`) matches the page's route. The match is
  case-sensitive. No match means the root locale.
- src/node/build/render.ts: <html lang> is siteData.lang from resolveSiteDataByRoute(), so the
  matched locale's lang, or the site's top-level lang (default en-US).
- src/node/plugins/localSearchPlugin.ts: each page goes into the search index of the locale that
  getLocaleForPath() returns.
So a folder of French pages whose name is not a key of `locales` (or differs from one only in
case or in '-' versus '_') is still published, but as root-locale pages: the root's <html lang>,
nav, labels and search index, and the language switcher does not list it.

Usage: python vitepress_locales.py <site root holding .vitepress> [--locales root,fr]
       [--src-dir docs] [--strict]
Prints one JSON report. Exit 0; with --strict, 1 if there is any finding; 2 if <root> has no
.vitepress folder.
"""
import argparse
import json
import os
import re
import sys

VITEPRESS_SHA = "40b2e090772ac11eac358d25ec92ee435fc2adbd"

# ISO 639-1 codes, plus a few common 3-letter primary tags.
LANG2 = frozenset((
    "aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu"
    " cv cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi"
    " ho hr ht hu hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks"
    " ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl"
    " nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl"
    " sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve"
    " vi vo wa wo xh yi yo za zh zu").split())
LANG3 = frozenset("ast ckb fil haw kab yue".split())

TAG_RE = re.compile(r"^([A-Za-z]{2,3})(?:[-_]([A-Za-z]{4}))?(?:[-_]([A-Za-z]{2}|[0-9]{3}))?$")
CONFIG_EXTS = (".mts", ".ts", ".mjs", ".js", ".cts", ".cjs")
DIR_CONFIG_NAMES = ("config.js", "config.mjs", "config.ts", "config.mts")
LOCALES_RE = re.compile(r"(?<![\w$.])locales\s*:\s*\{")
LOCALES_REF_RE = re.compile(r"(?<![\w$.])locales\b")
SRCDIR_RE = re.compile(r"""(?<![\w$.])srcDir\s*:\s*(['"])([^'"\n]+)\1""")
REWRITES_RE = re.compile(r"(?<![\w$.])rewrites\s*:")
SRCEXCLUDE_RE = re.compile(r"(?<![\w$.])srcExclude\s*:")
IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")
EXTERNAL_RE = re.compile(r"^(?:[a-z]+:|//)", re.I)
INDEX_OR_EXT_RE = re.compile(r"(?:(^|/)index)?(?:\.(?:md|html))?$")
FINDINGS = ("case_mismatch", "separator_mismatch", "unlisted")


def looks_like_lang(name):
    """True if a folder name has the shape of a language tag with a known primary language."""
    m = TAG_RE.match(name)
    if not m:
        return False
    primary = m.group(1).lower()
    return primary in LANG2 or primary in LANG3


def mask_code(text):
    """Blank out comments and string contents (quotes kept), keeping length and newlines.

    Braces, commas and colons inside strings or comments then no longer count as code.
    Regular-expression literals are not recognised (rare in VitePress configs).
    """
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            if j < 0:
                j = n
            for k in range(i, j):
                out[k] = " "
            i = j
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if text[k] != "\n":
                    out[k] = " "
            i = j
        elif c in "'\"`":
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == "\\":
                    j += 1
                elif c != "`" and text[j] == "\n":
                    break
                j += 1
            for k in range(i + 1, min(j, n)):
                if text[k] != "\n":
                    out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def _brace_depths(masked, positions):
    """Brace depth ('{' minus '}') of masked text just before each position."""
    want = set(positions)
    out = {}
    depth = 0
    for i, ch in enumerate(masked):
        if i in want:
            out[i] = depth
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
    return out


def find_locales_brace(masked, max_depth=1):
    """Index of the '{' opening the shallowest `locales: {` at brace depth <= max_depth, or None.

    The site's own locales sit at depth 1 (inside defineConfig({ ... })); deeper ones, such as
    themeConfig.search.options.locales, are search-box translations and are ignored.
    """
    matches = list(LOCALES_RE.finditer(masked))
    if not matches:
        return None
    depths = _brace_depths(masked, [m.start() for m in matches])
    ok = [m for m in matches if depths[m.start()] <= max_depth]
    if not ok:
        return None
    best = min(ok, key=lambda m: (depths[m.start()], m.start()))
    return best.end() - 1


def _segment_key(text, masked, a, b):
    """Classify one top-level entry text[a:b] of an object literal.

    Returns ("key", name), ("unknown", None) for spread or computed entries, or ("none", None).
    """
    seg = masked[a:b]
    stop = len(seg)
    for j, ch in enumerate(seg):
        if ch in ":{[(":
            stop = j
            break
    head = seg[:stop]
    lead = len(head) - len(head.lstrip())
    trail = len(head.rstrip())
    if trail <= lead:
        if stop < len(seg) and seg[stop] == "[":
            return ("unknown", None)
        return ("none", None)
    raw = text[a + lead:a + trail]
    if raw.startswith("..."):
        return ("unknown", None)
    if raw[0] in "'\"`" and len(raw) >= 2 and raw[-1] == raw[0]:
        if stop < len(seg) and seg[stop] != ":":
            return ("none", None)
        return ("key", raw[1:-1])
    if IDENT_RE.fullmatch(raw):
        if stop == len(seg) or seg[stop] == ":":
            return ("key", raw)
    return ("none", None)


def object_keys(text, masked, brace):
    """Top-level keys of the object literal whose '{' is at index brace.

    Returns (keys, has_unknown); has_unknown is True if a spread (...x) or computed ([k])
    entry was seen, so the key list may be incomplete.
    """
    keys = []
    unknown = False
    depth = 0
    seg_start = brace + 1
    for i in range(brace, len(masked)):
        ch = masked[i]
        end_segment = False
        closing = False
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
            if depth == 0:
                end_segment = closing = True
        elif ch == "," and depth == 1:
            end_segment = True
        if end_segment:
            kind, key = _segment_key(text, masked, seg_start, i)
            if kind == "key" and key not in keys:
                keys.append(key)
            elif kind == "unknown":
                unknown = True
            seg_start = i + 1
        if closing:
            break
    return keys, unknown


def config_candidates(root):
    """Config files: .vitepress/config.* or .vitepress/config/index.* first, then the others."""
    vp = os.path.join(root, ".vitepress")
    main, others = [], []
    for base in (vp, os.path.join(vp, "config")):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if not os.path.isfile(path) or not name.endswith(CONFIG_EXTS):
                continue
            if name.endswith(".d.ts"):
                continue
            stem = name.rsplit(".", 1)[0]
            if (base == vp and stem == "config") or (base != vp and stem == "index"):
                main.append(path)
            else:
                others.append(path)
    return main + others


def _rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def read_config(root):
    """Locale keys, srcDir and warnings from the site's config files (best effort, no JS run)."""
    info = {"keys": None, "unknown": False, "config": None, "src_dir": None,
            "locales_ref": False, "warnings": []}
    for path in config_candidates(root):
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        masked = mask_code(text)
        rel = _rel(path, root)
        if info["src_dir"] is None:
            for m in SRCDIR_RE.finditer(text):
                if masked[m.start()] != " ":
                    info["src_dir"] = m.group(2)
                    break
        if REWRITES_RE.search(masked):
            info["warnings"].append("rewrites set in %s: rewritten routes are not modelled" % rel)
        if SRCEXCLUDE_RE.search(masked):
            info["warnings"].append("srcExclude set in %s: excluded pages are still counted" % rel)
        if LOCALES_REF_RE.search(masked):
            info["locales_ref"] = True
        if info["keys"] is None:
            brace = find_locales_brace(masked)
            if brace is not None:
                keys, unknown = object_keys(text, masked, brace)
                info["keys"], info["unknown"], info["config"] = keys, unknown, rel
    if info["config"] is None:
        cands = config_candidates(root)
        if cands:
            info["config"] = _rel(cands[0], root)
    return info


def list_pages(src_dir):
    """Markdown pages under src_dir as sorted '/'-separated paths.

    Folders whose names start with '.' and node_modules folders are skipped by this checker.
    """
    pages = []
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith(".") and d != "node_modules")
        for name in filenames:
            if name.endswith(".md") and not name.startswith("."):
                rel = os.path.relpath(os.path.join(dirpath, name), src_dir)
                pages.append(rel.replace(os.sep, "/"))
    return sorted(pages)


def page_route(rel):
    """The route VitePress matches locales against: '/' + path, minus index and .md."""
    return INDEX_OR_EXT_RE.sub(lambda m: m.group(1) or "", "/" + rel, count=1)


def locale_for_page(rel, keys):
    """Port of getLocaleForPath(): first key whose ^/<key>/ matches the route, else 'root'."""
    route = page_route(rel)
    for key in keys:
        if key == "root" or EXTERNAL_RE.match(key):
            continue
        try:
            if re.search("^/" + key + "/", route):
                return key
        except re.error:
            continue
    return "root"


def _norm_tag(s):
    return s.lower().replace("_", "-")


def analyse(src_dir, keys):
    """Classify every top-level folder that is a locale key or looks like a language tag."""
    pages = list_pages(src_dir)
    loc_keys = [k for k in keys if k != "root"]
    by_top = {}
    for p in pages:
        if "/" in p:
            top, rest = p.split("/", 1)
            by_top.setdefault(top, []).append(rest)
    lang_dirs = set(d for d in by_top if looks_like_lang(d))
    root_tree = set()
    for p in pages:
        top = p.split("/", 1)[0] if "/" in p else None
        if top is None or (top not in lang_dirs and top not in loc_keys):
            root_tree.add(p)
    dirs = []
    for d in sorted(by_top):
        near = None
        status = None
        if d in loc_keys:
            status = "listed"
        else:
            near = next((k for k in loc_keys if k.lower() == d.lower()), None)
            if near is not None:
                status = "case_mismatch"
            else:
                near = next((k for k in loc_keys if _norm_tag(k) == _norm_tag(d)), None)
                if near is not None:
                    status = "separator_mismatch"
        if status is None and d not in lang_dirs:
            continue
        rest = by_top[d]
        mirrored = sum(1 for r in rest if r in root_tree)
        mirrors = mirrored >= 2 and mirrored * 2 >= len(rest)
        dir_config = any(os.path.isfile(os.path.join(src_dir, d, n)) for n in DIR_CONFIG_NAMES)
        if status is None:
            if not mirrors:
                status = "lang_like_not_mirrored"
            elif dir_config:
                status = "unlisted_dir_config"
            else:
                status = "unlisted"
        dirs.append({"dir": d, "status": status, "near_key": near, "pages": len(rest),
                     "mirrored_pages": mirrored,
                     "served_as": locale_for_page(d + "/" + rest[0], keys),
                     "dir_config": dir_config})
    empty = [k for k in loc_keys if not any(p.startswith(k + "/") for p in pages)]
    findings = sum(1 for x in dirs if x["status"] in FINDINGS)
    return {"pages": len(pages), "dirs": dirs, "empty_locales": empty, "findings": findings}


def analyse_site(root, locales=None, src_dir=None):
    """Full report for one site, or None if root has no .vitepress folder."""
    if not os.path.isdir(os.path.join(root, ".vitepress")):
        return None
    cfg = read_config(root)
    warnings = list(cfg["warnings"])
    if locales is not None:
        keys = [k.strip() for k in locales.split(",") if k.strip()]
        keys_from, complete = "--locales", True
    elif cfg["keys"] is not None:
        keys, keys_from, complete = cfg["keys"], cfg["config"], not cfg["unknown"]
        if not complete:
            warnings.append("locales has spread or computed entries, so its keys may be "
                            "incomplete: pass --locales")
    elif cfg["locales_ref"]:
        keys, keys_from, complete = [], None, False
        warnings.append("locales is set but not as an object literal at the top level: "
                        "pass --locales")
    else:
        keys, keys_from, complete = [], None, True
        warnings.append("no locales in the config: every page is served as the root locale")
    if src_dir is None:
        src_dir = cfg["src_dir"] or "."
    src = os.path.normpath(os.path.join(root, src_dir))
    if not os.path.isdir(src):
        warnings.append("srcDir %s does not exist" % src_dir)
    report = {"tool": "vitepress_locales",
              "vitepress_source": "vuejs/vitepress@" + VITEPRESS_SHA,
              "config": cfg["config"], "locales": keys, "locales_from": keys_from,
              "keys_complete": complete, "src_dir": src_dir.replace(os.sep, "/"),
              "warnings": warnings}
    report.update(analyse(src, keys))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Find translated folders a VitePress site serves under the wrong language.")
    ap.add_argument("root", help="site root, the folder that holds .vitepress")
    ap.add_argument("--locales", help="comma-separated locale keys, overriding the config")
    ap.add_argument("--src-dir", help="srcDir relative to root, overriding the config")
    ap.add_argument("--strict", action="store_true", help="exit 1 if there is any finding")
    args = ap.parse_args(argv)
    report = analyse_site(args.root, args.locales, args.src_dir)
    if report is None:
        print(json.dumps({"error": "no .vitepress folder in the given root"}))
        return 2
    print(json.dumps(report, indent=1, ensure_ascii=False))
    if args.strict and report["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
