#!/usr/bin/env python3
"""Call-site candidates for the translation-crash census (census_callsites
0.1.0, part (c) of census 0.4.1).

Census 0.4.0 calls a string "formatted" only when a getString /
stringResource / getQuantityString / pluralStringResource call names it
with arguments, or wraps a no-argument getString / stringResource in
String.format or .format(). The hand audit of its 40 "referenced" crash rows
(data/referenced-crash-audit.md) found 34 that throw, formatted in ways
those patterns miss. This keeps census 0.4.0's verdicts and adds a code use,
"candidate", for a "referenced" string whose references match one of these
rules (the first that matched is in findings.csv's new "callsite" column):

  wrapped  getString / getText / getQuantityString / pluralStringResource
           with no format arguments, wrapped in format(...) behind a
           receiver chain (getResources(). requireContext().) or followed
           by .format(...).
  fetched  the same lookups, stored in a variable that the same file passes
           to format(...) or calls .format(...) on.
  helper   R.string.x is a whole argument of another call, followed by an
           argument that is not a resource id, constant or literal
           (Builder.content(id, args), logInfo(id, name),
           StringUtil.format(context, id, name)). Toast.makeText, setText,
           setTitle and other display calls don't count.
  stored   the id is kept, passed or returned (val id = if ... R.string.a
           else ..., return R.plurals.x, a list or a constructor), and some
           .kt/.java file in the repository formats a string id it doesn't
           name literally (getString(resId, args), getQuantityString(f(), n,
           n), String.format(getString(id), x)).

"candidate" means the call site needs reading, not that the crash is
reachable.

  python census_callsites.py --data-dir /data --out-dir /out   # same options as census.py

Writes census.py's apps.jsonl, findings.csv (with a callsite column),
summary.json and report.md, and callsites.json, which scores the predictions
in PREDICTIONS.md against the hand audit (referenced-crash-audit.csv). The
predictions were published before this ran; the job refuses to run until
they are on main.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import collections
import csv
import json
import os
import re
import sys
import threading
import urllib.request

import census
import census_plurals

__version__ = "0.1.0"

REPO_RAW = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
PREDICTIONS_URL = REPO_RAW + "callsites/PREDICTIONS.md"
PREDICTIONS_MARK = "census_callsites 0.1.0 predictions"
AUDIT = "referenced-crash-audit.csv"
THROWS = ("crash", "throws, caught", "throws, trigger not confirmed")
NOT_FORMATTED = ("safe (not formatted)",)

RULES = ("wrapped", "fetched", "helper", "stored")
STRING_LOOKUPS = {"getString", "stringResource", "getText"}
PLURAL_LOOKUPS = {"getQuantityString", "pluralStringResource", "getQuantityText"}
LOOKUPS = STRING_LOOKUPS | PLURAL_LOOKUPS
# Calls that show or compare an id without formatting it.
NOT_FORMAT_CALLS = LOOKUPS | {
    "makeText", "make", "setText", "setTitle", "setSubtitle", "setMessage", "setHint", "setSummary",
    "setContentDescription", "setPositiveButton", "setNegativeButton", "setNeutralButton",
    "setContentTitle", "setContentText", "setTicker", "setLabel", "setTooltipText", "addAction",
    "Text", "if", "while", "for", "switch", "when", "catch", "synchronized", "equals"}
# Calls that only hold ids; an id in one counts as stored, never as a helper.
CONTAINERS = {"listOf", "mutableListOf", "arrayListOf", "arrayOf", "intArrayOf", "setOf", "mapOf",
              "mutableMapOf", "hashMapOf", "asList", "of", "Pair", "Triple", "to", "put", "add"}

_RECEIVER = r"(?:[\w.?!]|\(\s*\))*"
_LOCALE = r"(?:[\w.]*Locale[\w.()]*\s*,\s*)?"
_WRAP_RE = re.compile(r"format\s*\(\s*" + _LOCALE + _RECEIVER + r"$")
_AFTER_RE = re.compile(r"\s*(?:\.\s*toString\s*\(\s*\)\s*)?\.\s*format\s*\(")
_ASSIGN_RE = re.compile(r"\b(\w+)\s*(?::\s*[\w.<>?]+\s*)?=\s*" + _RECEIVER + r"$")
_LOOKUP_RE = re.compile(r"\b(%s)\s*\(" % "|".join(sorted(LOOKUPS)))
_ID_LITERAL_RE = re.compile(r"\s*(?:\w+\s*=\s*)?(?:\w*R|Res)\.\w+\.\w+\s*$")
_WHOLE_RE = re.compile(r"\s*(?:\w+\s*=\s*)?(?:\w*R|Res)\.(?:string|plurals)\.\w+\s*")
_PLAIN_RE = re.compile(r"\s*(?:\w+\s*=\s*)?(?:(?:\w*R|Res)\.\w+\.\w+|(?:[\w.]+\.)?[A-Z][A-Z0-9_]+"
                       r"|-?\d[\w.]*|true|false|null|this)\s*")
_LAST_NAME_RE = re.compile(r"(\w+)\s*(?:\(\s*\))?[\s!?]*$")
_ID_NAME_RE = re.compile(r"(?:Id|ID|Res|RES|Resource|Title|Message|Msg|Text|Label|Format|String)$")
_ID_NAMES = {"id", "res", "resid", "title", "message", "msg", "text", "label", "format"}

_lock = threading.Lock()
_local = threading.local()
_code_uses_040 = None
_process_repo_040 = None
CALLSITE = {}  # (repo web URL, (kind, name)) -> rule
TOTALS = collections.Counter()


# --------------------------------------------------------------- parsing

def _split_args(text, open_at, limit=3000):
    """([(start, end)] of the top-level arguments, index of the closing ')')
    for the call whose '(' is at text[open_at], or None if it doesn't close
    within limit characters."""
    spans, depth, start, i, quote = [], 0, open_at + 1, open_at + 1, None
    end = min(len(text), open_at + limit)
    while i < end:
        c = text[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = None
        elif c == '"':
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                if text[start:i].strip():
                    spans.append((start, i))
                return spans, i
            depth -= 1
        elif c == "," and depth == 0:
            spans.append((start, i))
            start = i + 1
        i += 1
    return None


def _open_paren(text, start):
    """Index of the '(' whose argument list holds text[start], or None when
    a '{' or '[' (a block, lambda or index) comes first."""
    depth, i = 0, start - 1
    while i >= 0 and start - i < 400:
        c = text[i]
        if c in ")]}":
            depth += 1
        elif c in "([{":
            if depth == 0:
                return i if c == "(" else None
            depth -= 1
        i -= 1
    return None


def _call_name(text, open_at):
    m = census._CALL_NAME_RE.search(text, max(0, open_at - 80), open_at)
    return (m.group(1), m.start(1)) if m else ("", open_at)


def _formatted_later(text, name_at, close):
    """"wrapped" or "fetched" if the lookup call at text[name_at:close+1]
    ends up in format(...), else None."""
    if _WRAP_RE.search(text, max(0, name_at - 160), name_at):
        return "wrapped"
    if _AFTER_RE.match(text, close + 1):
        return "wrapped"
    a = _ASSIGN_RE.search(text, max(0, name_at - 160), name_at)
    if a:
        v = re.escape(a.group(1))
        if re.search(r"format\s*\(\s*%s(?:this\.)?%s\s*,|\b%s\s*(?:\.\s*toString\s*\(\s*\)\s*)?"
                     r"\.\s*format\s*\(" % (_LOCALE, v, v), text):
            return "fetched"
    return None


def _id_like(first):
    """True if a lookup's first argument reads as a resource id (resId,
    messageStringId, getAgoStringResID(), chartConfig.title), not a
    preference key, column index or string literal."""
    m = _LAST_NAME_RE.search(first)
    if not m:
        return False
    name = m.group(1)
    return bool(_ID_NAME_RE.search(name)) or name.lower() in _ID_NAMES


def has_dynamic(text):
    """True if the file formats a string id it doesn't name literally."""
    for m in _LOOKUP_RE.finditer(text):
        name = m.group(1)
        parsed = _split_args(text, m.end() - 1)
        if not parsed or not parsed[0]:
            continue
        spans, close = parsed
        first = text[spans[0][0]:spans[0][1]]
        if _ID_LITERAL_RE.match(first):
            continue
        if name in ("getString", "getText", "getQuantityText") and not _id_like(first):
            continue
        need = 3 if name in PLURAL_LOOKUPS else 2
        if (len(spans) >= need and name not in ("getText", "getQuantityText")) \
                or _formatted_later(text, m.start(1), close):
            return True
    return False


def _helper(text, open_at, start, end):
    parsed = _split_args(text, open_at)
    if not parsed:
        return False
    spans, _ = parsed
    for k, (s, e) in enumerate(spans):
        if s <= start and end <= e:
            if not _WHOLE_RE.fullmatch(text, s, e):
                return False
            return any(not _PLAIN_RE.fullmatch(text, s2, e2) for s2, e2 in spans[k + 1:])
    return False


def reason(text, start, end):
    """The rule the reference at text[start:end] matches ("stored" still
    needs a repository that formats ids), or None."""
    open_at = _open_paren(text, start)
    if open_at is None:
        return "stored"
    name, name_at = _call_name(text, open_at)
    if name in LOOKUPS:
        parsed = _split_args(text, open_at)
        if not parsed or not parsed[0]:
            return None
        spans, close = parsed
        if not (spans[0][0] <= start and end <= spans[0][1]):
            return None
        if len(spans) > (2 if name in PLURAL_LOOKUPS else 1):
            return None  # passes arguments: census 0.4.0 already says formatted
        return _formatted_later(text, name_at, close)
    if name in NOT_FORMAT_CALLS:
        return None
    if name and name not in CONTAINERS and _helper(text, open_at, start, end):
        return "helper"
    return "stored"


def _code_files(root):
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in files:
            if name.endswith((".kt", ".java")):
                yield os.path.join(dirpath, name)


def candidates(root, names):
    """{(kind, name): rule} for those of names (strings census 0.4.0 calls
    "referenced") whose references match a rule."""
    if not names:
        return {}
    fields = {(kind, n.replace(".", "_")): (kind, n) for kind, n in names}
    pattern = re.compile(r"\b(?:\w*R|Res)\.(string|plurals)\.(%s)\b"
                         % "|".join(sorted(re.escape(n) for _, n in fields)))
    found, pending, dynamic = {}, set(), False
    for path in _code_files(root):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        if not dynamic and has_dynamic(text):
            dynamic = True
        for m in pattern.finditer(text):
            key = fields.get((m.group(1), m.group(2)))
            if key is None:
                continue
            why = reason(text, m.start(), m.end())
            if why == "stored":
                pending.add(key)
            elif why and RULES.index(why) < RULES.index(found.get(key, "stored")):
                found[key] = why
    if dynamic:
        for key in pending:
            found.setdefault(key, "stored")
    return found


# --------------------------------------------------------------- census

def code_uses(root, names):
    """census 0.4.0's code_uses, with "candidate" for referenced strings
    whose call sites match a rule."""
    uses = _code_uses_040(root, names)
    referenced = {n for n, u in uses.items() if u == "referenced"}
    try:
        found = candidates(root, referenced)
    except Exception:  # keep census 0.4.0's answer
        found = {}
        with _lock:
            TOTALS["callsite_errors"] += 1
    for key in found:
        uses[key] = "candidate"
    _local.found = found
    with _lock:
        TOTALS["referenced_names"] += len(referenced)
        TOTALS["candidate_names"] += len(found)
        for why in found.values():
            TOTALS["candidate_names_" + why] += 1
    return uses


def process_repo(repo, timeout, tmp_root):
    _local.found = {}
    record, pairs = _process_repo_040(repo, timeout, tmp_root)
    found = getattr(_local, "found", {}) or {}
    _local.found = {}
    if found:
        with _lock:
            for key, why in found.items():
                CALLSITE[(repo["web"], key)] = why
    record["callsite_candidates"] = len(found)
    return record, pairs


def apply():
    """census 0.4.0 (census_plurals) with call-site candidates. Safe to call twice."""
    global _code_uses_040, _process_repo_040
    census_plurals.apply()
    if census.code_uses is not code_uses:
        _code_uses_040 = census.code_uses
        census.code_uses = code_uses
    if census.process_repo is not process_repo:
        _process_repo_040 = census.process_repo
        census.process_repo = process_repo
    census.USES = ("formatted", "candidate", "referenced", "unreferenced", "unknown")


# --------------------------------------------------------------- scoring

def audit_rows(findings, audit):
    """Each hand-audited row with what this run says about it."""
    rows = []
    for a in audit:
        tail = "/" + a["repo"].lower()
        hits = [r for r in findings if r["repo"].lower().rstrip("/").endswith(tail)
                and r["locale"] == a["locale"] and r["key"] == a["key"]]
        hits.sort(key=lambda r: r["verdict"] != "crash")
        r = hits[0] if hits else {}
        rows.append({"repo": a["repo"], "locale": a["locale"], "key": a["key"],
                     "audit": a["verdict"], "found": bool(r), "verdict": r.get("verdict", ""),
                     "use": r.get("use", ""), "callsite": r.get("callsite", "")})
    return rows


def predictions(rows, totals):
    throws = [r for r in rows if r["audit"] in THROWS and r["verdict"] == "crash"]
    hit = [r for r in throws if r["use"] in ("formatted", "candidate")]
    plain = [r for r in rows if r["audit"] in NOT_FORMATTED and r["found"]]
    ref, cand = totals.get("referenced_names", 0), totals.get("candidate_names", 0)
    return [
        {"id": "C1", "text": "at least 80%% of the hand-audited rows that throw, still crashing, are "
         "formatted or candidate: %d of %d" % (len(hit), len(throws)),
         "held": bool(throws) and len(hit) * 5 >= len(throws) * 4},
        {"id": "C2", "text": "the hand-audited rows that are not formatted stay referenced: %s"
         % ", ".join("%s %s=%s" % (r["locale"], r["key"], r["use"]) for r in plain),
         "held": all(r["use"] == "referenced" for r in plain) if plain else None},
        {"id": "C3", "text": "at most half of the strings census 0.4.0 calls referenced become "
         "candidates: %d of %d" % (cand, ref),
         "held": cand * 2 <= ref if ref else None},
    ]


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-census-callsites"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def _label(held):
    return "NOT TESTABLE" if held is None else "HELD" if held else "FAILED"


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if "--no-gate" in args:
        args.remove("--no-gate")
    else:
        try:
            pred = _fetch(PREDICTIONS_URL)
        except Exception as exc:
            pred = ""
            print("gate: could not read PREDICTIONS.md on main: %s" % exc)
        if PREDICTIONS_MARK not in pred:
            print("gate: predictions not on main; refusing to run")
            return 3
    apply()
    out_dir = "/out"
    if "--out-dir" in args:
        out_dir = args[args.index("--out-dir") + 1]
    code = census.main(args)

    path = os.path.join(out_dir, "findings.csv")
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        findings = list(reader)
    for r in findings:
        r["callsite"] = CALLSITE.get((r["repo"], census._resource(r["key"])), "")
    with open(path, "w", encoding="utf-8", errors="replace", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields + ["callsite"])
        writer.writeheader()
        writer.writerows(findings)

    with open(os.path.join(out_dir, "summary.json"), encoding="utf-8") as f:
        summary = json.load(f)
    audit_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), AUDIT)
    with open(audit_path, encoding="utf-8", newline="") as f:
        audit = list(csv.DictReader(f))
    rows = audit_rows(findings, audit)
    checks = predictions(rows, TOTALS)
    by_rule = collections.Counter(r["callsite"] for r in findings
                                  if r["verdict"] == "crash" and r["use"] == "candidate")
    commit = ""
    if os.path.isfile("census_commit.txt"):
        with open("census_commit.txt") as f:
            commit = f.read().strip()
    result = dict(TOTALS, version=__version__, census_version=census.__version__,
                  census_commit=commit, pairs=summary.get("formatted_translation_pairs"),
                  verdicts=summary.get("verdicts"), crash_by_code_use=summary.get("crash_by_code_use"),
                  crash_candidates_by_rule=dict(by_rule.most_common()),
                  repos_attempted=summary.get("repos_attempted"),
                  repos_not_reached=summary.get("repos_not_reached"),
                  audit=rows, predictions=checks)
    with open(os.path.join(out_dir, "callsites.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("callsites: %d referenced strings, %d candidates %s; crash by code use %s; crash "
          "candidates by rule %s"
          % (TOTALS["referenced_names"], TOTALS["candidate_names"],
             json.dumps({k: v for k, v in TOTALS.items() if k.startswith("candidate_names_")}),
             json.dumps(result["crash_by_code_use"]), json.dumps(result["crash_candidates_by_rule"])),
          flush=True)
    for r in rows:
        print("audit %s %s %s [%s]: %s %s %s" % (r["repo"], r["locale"], r["key"], r["audit"],
                                                r["verdict"] or "not found", r["use"], r["callsite"]))
    for p in checks:
        print("%s %s: %s" % (p["id"], _label(p["held"]), p["text"]), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
