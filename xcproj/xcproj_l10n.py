# xcproj_l10n: find translated Apple string tables (<lang>.lproj/<Table>.strings) that are
# committed to a repository but never registered in the app's Xcode 27.2+ JSON project file
# (<Name>.xcodeproj/project.xcproj), so Xcode never builds them into the app.
#
# Written from the published model of the format in Apple's xcode-project-format package
# (github.com/apple/xcode-project-format, Apache-2.0 WITH Swift-exception), read on 2026-11-12:
#   - the file is JSON with comments and trailing commas;
#   - "files" is the navigator tree; each node has "kind" = file-reference (the default when
#     "kind" is missing) | group | folder | variant-group | version-group;
#   - a node's location is one "path" string: a bare relative path is relative to the parent
#     node's folder, "<PROJECT>/..." is relative to the folder that holds the .xcodeproj, and
#     "<DEVELOPER>/", "<SDK>/", "<PRODUCTS>/", "<USER:VAR>/" and absolute paths are outside
#     the repository;
#   - a variant-group (a localized resource) lists every language as a child file reference
#     whose path carries the .lproj folder ("de.lproj/Localizable.strings"); file references
#     have no "name", so the language comes from the path;
#   - a "folder" is a synchronized folder: everything inside it is in the project;
#   - "localizations" = {"development": "en", "supported": [...]} and, unlike knownRegions in
#     project.pbxproj, "supported" does NOT include the development language.
# The same rules as MV2's xcode-lproj census v3 decide what is "lost": only tables that the
# project registers at least one language of count; English, Base and a regional copy of a
# language the table already ships never count. Unverified against Xcode itself: how "<" in a
# path is escaped (assumed "\<"), and nodes this reader does not know are skipped.
#
# Standard library only. Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import json
import os
import re
import sys

PROJECT_FILE = "project.xcproj"
PROJECT_SUFFIX = ".xcodeproj/" + PROJECT_FILE
LPROJ_RE = re.compile(r"^(?:(.*)/)?([^/]+)\.lproj/([^/]+\.strings)$")
REGION_RE = re.compile(r"^([A-Za-z]{2,3})[-_]([A-Za-z]{2}|[0-9]{3})$")
VENDOR = frozenset(["pods", "carthage", "node_modules", "vendor", "vendors", "third_party",
                    "thirdparty", "third-party", "3rdparty", "external", "externals",
                    "submodules", "deps", "build", "deriveddata", ".build", "sourcepackages",
                    "checkouts"])
BUNDLE_SUFFIXES = (".framework", ".xcframework", ".bundle", ".app", ".appex")
MAX_DEPTH = 64


# ------------------------------------------------------------------ reading the file

def strip_json5(text):
    """Remove // and /* */ comments and trailing commas that sit outside strings."""
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "/" and text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                raise ValueError("unterminated block comment")
            out.append(" ")
            i = j + 2
            continue
        out.append(c)
        i += 1
    s = "".join(out)
    out = []
    i, n = 0, len(s)
    in_str = False
    while i < n:
        c = s[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(s[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
        elif c == ",":
            j = i + 1
            while j < n and s[j] in " \t\r\n":
                j += 1
            if j < n and s[j] in "]}":
                i += 1
                continue
        out.append(c)
        i += 1
    return "".join(out)


def loads_xcproj(text):
    if text.startswith(chr(0xFEFF)):
        text = text[1:]
    return json.loads(strip_json5(text))


# ------------------------------------------------------------------ paths

def norm(path):
    """Repository path with '.' and '..' resolved, or None if it leaves the repository."""
    out = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not out:
                return None
            out.pop()
        else:
            out.append(part)
    return "/".join(out)


def resolve(base_dir, path, src_root):
    """Repository path of a node, or None when it is outside the repository.
    base_dir: the parent node's folder (None if unknown); src_root: the folder holding the
    .xcodeproj."""
    if not isinstance(path, str):
        path = ""
    if path.startswith("<PROJECT>/"):
        return norm(src_root + "/" + path[len("<PROJECT>/"):])
    if path.startswith("<") or path.startswith("/") or path.startswith("~"):
        return None
    if base_dir is None:
        return None
    path = path.replace("\\<", "<")
    return norm(base_dir + "/" + path) if path else base_dir


def project_refs(proj_path, data):
    """(refs, regions) for one project.xcproj, the same contract as the census reader for
    project.pbxproj. refs: repository paths of every file reference (variant-group children
    included), synchronized folder and version group; regions: the development language
    followed by the supported ones (the knownRegions equivalent)."""
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise ValueError("no files list")
    src_root = proj_path.rpartition("/")[0].rpartition("/")[0]
    refs = set()

    def walk(nodes, base, depth):
        if depth > MAX_DEPTH:
            raise ValueError("file tree deeper than %d" % MAX_DEPTH)
        for node in nodes:
            if not isinstance(node, dict):
                continue
            kind = node.get("kind", "file-reference")
            raw = node.get("path", "")
            p = resolve(base, raw, src_root)
            if kind in ("group", "variant-group", "version-group"):
                if kind == "version-group" and raw and p is not None:
                    refs.add(p)
                children = node.get("children")
                if isinstance(children, list):
                    walk(children, p, depth + 1)
            elif kind in ("file-reference", "folder"):
                if raw and p is not None:
                    refs.add(p)

    walk(data["files"], src_root, 0)
    regions = []
    loc = data.get("localizations")
    if isinstance(loc, dict):
        dev = loc.get("development")
        if isinstance(dev, str):
            regions.append(dev)
        sup = loc.get("supported")
        if isinstance(sup, list):
            for x in sup:
                if isinstance(x, str) and x not in regions:
                    regions.append(x)
    return refs, regions


# ------------------------------------------------------------------ rules

def covered(path, refs):
    """True if the path, or a folder above it, is referenced."""
    parts = path.split("/")
    for i in range(len(parts) + 1):
        if "/".join(parts[:i]) in refs:
            return True
    return False


def is_vendored(path):
    for part in path.split("/"):
        low = part.lower()
        if low in VENDOR or low.endswith(BUNDLE_SUFFIXES):
            return True
    return False


def english(lang):
    low = lang.lower()
    return low in ("base", "english", "en") or low.startswith(("en-", "en_"))


def regional_copy(lang, shipped):
    """True for lang_REGION / lang-REGION (2 letters or 3 digits) when the plain language is
    already shipped by the same table. Script subtags (zh-Hant) are never regional copies."""
    m = REGION_RE.match(lang)
    if not m:
        return False
    base = m.group(1).lower()
    return any(s.lower() == base for s in shipped)


def analyse(paths, reader):
    """paths: every file path in the repository ('/' separators); reader(path) -> bytes or
    None. Returns the projects read, the number of registered tables, the lost files and the
    files skipped by rule."""
    pathset = set(paths)
    res = {"projects": [], "managed_tables": 0, "lost": [], "skipped": {}, "regions": []}
    refs, regions = set(), []
    for p in sorted(x for x in paths if x.endswith(PROJECT_SUFFIX) and not is_vendored(x)):
        rec = {"path": p, "status": "ok", "refs": 0, "regions": [],
               "pbxproj_too": p[:-len(PROJECT_FILE)] + "project.pbxproj" in pathset}
        data = reader(p)
        if data is None:
            rec["status"] = "unread"
        else:
            try:
                r, kr = project_refs(p, loads_xcproj(data.decode("utf-8-sig")))
            except (ValueError, RecursionError) as exc:
                rec["status"] = ("parse error: %s" % (exc,))[:160]
            else:
                refs |= r
                rec["refs"] = len(r)
                rec["regions"] = kr
                for x in kr:
                    if x not in regions:
                        regions.append(x)
        res["projects"].append(rec)
    res["regions"] = regions
    tables, shipped_any = {}, set()
    for p in paths:
        m = LPROJ_RE.match(p)
        if not m or is_vendored(p):
            continue
        if covered(p, refs):
            shipped_any.add(m.group(2))
        tables.setdefault((m.group(1) or "", m.group(3)), {})[m.group(2)] = p
    for (d, name) in sorted(tables):
        langs = tables[(d, name)]
        if not any(langs[lang] in refs for lang in langs):
            continue
        res["managed_tables"] += 1
        shipped = set(lang for lang in langs if covered(langs[lang], refs))
        for lang in sorted(langs):
            if lang in shipped:
                continue
            if english(lang):
                skip = "english"
            elif regional_copy(lang, shipped):
                skip = "regional copy"
            else:
                skip = ""
            if skip:
                res["skipped"][skip] = res["skipped"].get(skip, 0) + 1
                continue
            res["lost"].append({"dir": d, "table": name, "lang": lang, "path": langs[lang],
                                "in_regions": lang in regions,
                                "whole": lang not in shipped_any})
    return res


def scan_dir(root):
    """analyse() over a checked-out repository folder (.git skipped)."""
    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        rel = "" if rel == "." else rel
        for f in sorted(filenames):
            paths.append(f if not rel else rel + "/" + f)

    def reader(p):
        try:
            with open(os.path.join(root, *p.split("/")), "rb") as fh:
                return fh.read()
        except OSError:
            return None

    return analyse(paths, reader)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    strict = "--strict" in argv
    root = args[0] if args else "."
    res = scan_dir(root)
    print(json.dumps(res, indent=1, sort_keys=True))
    if not res["projects"]:
        print("no %s found under %s" % (PROJECT_SUFFIX, root), file=sys.stderr)
    return 1 if (strict and res["lost"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
