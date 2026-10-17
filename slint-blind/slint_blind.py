# Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made by MV2 of Munim, Inc. with AI agents.
"""A fourth open-source check, i18n-security-lint 0.2.1, run over the census's crashing translations.

i18n-security-lint (ecogetaway/oss-language-inclusion, Apache-2.0, on PyPI) scans locale files for
bidi controls, script injection and "format-specifier tampering". This runs its placeholder
comparison over the same 366 crashing rows checks_blind.py ran Weblate, pofilter and Android Lint
over (data/checks-blind-rows.csv, pinned below), in three ways:

1. api: compare_placeholders(source, translation) on each row's text, the check alone.
2. po: each row written as a one-entry .po file and scanned by the tool's own CLI (--json), the
   only file type in which the tool pairs a translation with its source.
3. xliff and android: the same kind of pairs as an XLIFF file with <source> and <target>, and as
   an Android res/ tree (values/strings.xml + values-es/strings.xml), scanned by the CLI.

The tool is installed from PyPI and called, never copied. Its findings are counted as "flagged"
when any finding has a rule ending in _DRIFT (FORMAT_SPECIFIER_DRIFT or INTERPOLATION_DRIFT).
PREDICTIONS.md was written before the first run.

Usage: python slint_blind.py --url URL --out-dir out
       python slint_blind.py checks-blind-rows.csv --out-dir out
"""

import argparse
import collections
import contextlib
import csv
import io
import json
import os
import tempfile
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

VERSION = "0.1.0"
ROWS_URL = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
            "50cd0ac6baf1e8f31baa05f221eaf803e6f39d63/data/checks-blind-rows.csv")
OTHERS = ("weblate", "pofilter", "lint")
# The 12 rows checks_blind.py 0.1.0 found no check sees (data/checks-blind.md).
NONE_SEEN = 12
POFILTER_FLAGGED = 322

# Android pairs for the res/ tree: (name, English, Spanish). Each Spanish text throws in
# java.util.Formatter with the argument the English implies.
ANDROID_PAIRS = [
    ("files_count", "%1$s files", "%1$d archivos"),
    ("percent_done", "%1$d%% done", "%1$d% hecho"),
    ("missing_letter", "Sent to %1$s", "Enviado a %1$"),
]


def read_rows(path=None, url=None):
    if path:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    else:
        with urllib.request.urlopen(url, timeout=120) as r:
            text = r.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text, newline="")))


def is_flagged(rules):
    return any(r.endswith("_DRIFT") for r in rules)


def api_rules(compare, source, translation):
    return sorted({f.rule for f in compare(source, translation)})


def po_quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def po_entry(source, translation):
    return "msgid %s\nmsgstr %s\n" % (po_quote(source), po_quote(translation))


def xliff_doc(pairs):
    units = ['<trans-unit id="r%04d"><source>%s</source><target>%s</target></trans-unit>'
             % (i, escape(s), escape(t)) for i, (s, t) in enumerate(pairs)]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<xliff version="1.2"><file source-language="en" '
            'target-language="xx" datatype="plaintext" original="census"><body>\n'
            + "\n".join(units) + "\n</body></file></xliff>\n")


def android_xml(items):
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>"]
    lines += ['    <string name="%s">%s</string>' % (n, escape(t)) for n, t in items]
    return "\n".join(lines + ["</resources>", ""])


def run_cli(main, args):
    """(exit code, parsed --json output or None, error text) from the tool's own main()."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = main(list(args))
    except SystemExit as e:
        rc = e.code
    except Exception as e:  # recorded, not hidden
        return None, None, "%s: %s" % (type(e).__name__, e)
    out = buf.getvalue()
    parsed = None
    if "--json" in args:
        i = out.find("{")
        parsed = json.loads(out[i:]) if i >= 0 else {}
    return rc, parsed, ""


def cli_rules(parsed):
    return sorted({f.get("rule", "") for locs in (parsed or {}).values() for fs in locs.values() for f in fs})


def summarise(rows, api, po):
    """rows: census rows; api/po: per-row rule lists (po entries may be None for a CLI error)."""
    out_rows = []
    for r, a, p in zip(rows, api, po):
        others = [c for c in OTHERS if r.get(c) == "flagged"]
        out_rows.append(dict(app=r["app"], repo=r["repo"], locale=r["locale"], key=r["key"], use=r["use"],
                             exception=r["exception"], kind=r["kind"],
                             slint_api="flagged" if is_flagged(a) else "unflagged", slint_api_rules=" ".join(a),
                             slint_po="error" if p is None else ("flagged" if is_flagged(p) else "unflagged"),
                             slint_po_rules="" if p is None else " ".join(p),
                             pofilter=r["pofilter"], others_seen_by=" ".join(others), source=r["source"],
                             translation=r["translation"]))
    groups = {}
    for name, sel in (("all-crash", out_rows), ("formatted-crash", [e for e in out_rows if e["use"] == "formatted"])):
        g = {"rows": len(sel), "repos": len({e["repo"] for e in sel}),
             "slint_api": dict(collections.Counter(e["slint_api"] for e in sel)),
             "slint_po": dict(collections.Counter(e["slint_po"] for e in sel)),
             "slint_only": sum(1 for e in sel if e["slint_api"] == "flagged" and not e["others_seen_by"]),
             "none_of_three": sum(1 for e in sel if not e["others_seen_by"]),
             "none_of_four": sum(1 for e in sel if e["slint_api"] != "flagged" and not e["others_seen_by"]),
             "by_kind": {}}
        for kind in sorted({e["kind"] for e in sel}):
            k = [e for e in sel if e["kind"] == kind]
            g["by_kind"][kind] = {"rows": len(k), "slint_flagged": sum(1 for e in k if e["slint_api"] == "flagged"),
                                  "pofilter_flagged": sum(1 for e in k if e["pofilter"] == "flagged")}
        groups[name] = g
    return out_rows, groups


def predictions(groups, out_rows, android, xliff_drift):
    allc = groups["all-crash"]
    flagged = allc["slint_api"].get("flagged", 0)
    agree = sum(1 for e in out_rows if e["slint_po"] == e["slint_api"])
    return [
        ("P1", "android res/ tree and strings.xml named directly: no findings; --strict exits 0",
         all(a["findings"] == 0 and a["strict_rc"] == 0 for a in android.values())),
        ("P2", "XLIFF with <source> and <target>: 0 drift findings", xliff_drift == 0),
        ("P3", "the %d rows no other check sees: 0 flagged" % NONE_SEEN,
         allc["none_of_three"] == NONE_SEEN and allc["slint_only"] == 0),
        ("P4", "fewer than pofilter's %d of 366 flagged (api)" % POFILTER_FLAGGED, flagged < POFILTER_FLAGGED),
        ("P5", "po path agrees with api path on at least 360 of %d rows" % len(out_rows), agree >= 360),
    ], flagged, agree


def report(meta, groups, preds, android, xliff_drift, unseen):
    lines = ["# i18n-security-lint over the census's crashing translations", "",
             "slint_blind.py %s (MV2 of Munim, Inc., made with AI agents), i18n-security-lint %s from PyPI, "
             "rows from data/checks-blind-rows.csv at %s." % (VERSION, meta["slint_version"], meta["rows_commit"]),
             "", "## Predictions (PREDICTIONS.md, written before the run)", ""]
    lines += ["- %s %s: %s" % (pid, "HELD" if ok else "FAILED", text) for pid, text, ok in preds]
    lines += ["", "## File paths", ""]
    for name, a in android.items():
        lines.append("- android %s: %d findings, --strict exit %s%s" % (
            name, a["findings"], a["strict_rc"], ("; error " + a["error"]) if a["error"] else ""))
    lines.append("- xliff (%d pairs with <source>): %d drift findings" % (meta["rows"], xliff_drift))
    for name, g in groups.items():
        lines += ["", "## %s: %d rows in %d repositories" % (name, g["rows"], g["repos"]), "",
                  "- api: %s" % ", ".join("%s %d" % kv for kv in sorted(g["slint_api"].items())),
                  "- po file through the CLI: %s" % ", ".join("%s %d" % kv for kv in sorted(g["slint_po"].items())),
                  "- flagged by i18n-security-lint and by none of Weblate, pofilter, Lint: %d" % g["slint_only"],
                  "- seen by none of the three: %d; by none of the four: %d" % (g["none_of_three"], g["none_of_four"]),
                  "", "| mistake kind | rows | i18n-security-lint | pofilter |", "|---|---:|---:|---:|"]
        for kind, v in g["by_kind"].items():
            lines.append("| %s | %d | %d | %s |" % (kind, v["rows"], v["slint_flagged"], v["pofilter_flagged"]))
    lines += ["", "## Crashing rows i18n-security-lint does not flag (formatted first)", ""]
    for e in unseen:
        lines.append("- %s | %s %s `%s` | `%s` -> `%s` (%s, %s; others: %s)" % (
            e["kind"], e["app"], e["locale"], e["key"], e["source"].replace("\n", " "),
            e["translation"].replace("\n", " "), e["exception"], e["use"], e["others_seen_by"] or "none"))
    return "\n".join(lines) + "\n"


FIELDS = ["app", "repo", "locale", "key", "use", "exception", "kind", "slint_api", "slint_api_rules", "slint_po",
          "slint_po_rules", "pofilter", "others_seen_by", "source", "translation"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", nargs="?")
    ap.add_argument("--url", default=ROWS_URL)
    ap.add_argument("--out-dir", default="out")
    a = ap.parse_args()

    from importlib.metadata import version
    from i18n_security_lint.cli import main as slint_main
    from i18n_security_lint.extract import extract
    from i18n_security_lint.scanners import compare_placeholders

    rows = read_rows(a.rows, None if a.rows else a.url)
    api = [api_rules(compare_placeholders, r["source"], r["translation"]) for r in rows]

    tmp = Path(tempfile.mkdtemp(prefix="slint-"))
    po, errors = [], []
    for i, r in enumerate(rows):
        p = tmp / "po" / ("%04d.po" % i)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(po_entry(r["source"], r["translation"]), encoding="utf-8")
        _, parsed, err = run_cli(slint_main, ["--json", str(p)])
        if err:
            errors.append("%04d: %s" % (i, err))
            po.append(None)
        else:
            po.append(cli_rules(parsed))

    xl = tmp / "census.xlf"
    xl.write_text(xliff_doc([(r["source"], r["translation"]) for r in rows]), encoding="utf-8")
    _, xparsed, xerr = run_cli(slint_main, ["--json", str(xl)])
    xliff_drift = -1 if xerr else sum(1 for rule in cli_rules(xparsed) if rule.endswith("_DRIFT"))
    xliff_entries = len(list(extract(xl)))

    res = tmp / "app" / "src" / "main" / "res"
    (res / "values").mkdir(parents=True)
    (res / "values-es").mkdir(parents=True)
    (res / "values" / "strings.xml").write_text(android_xml([(n, s) for n, s, _ in ANDROID_PAIRS]), encoding="utf-8")
    (res / "values-es" / "strings.xml").write_text(android_xml([(n, t) for n, _, t in ANDROID_PAIRS]),
                                                   encoding="utf-8")
    android = {}
    for name, target in (("res-directory", res), ("values-es-strings.xml", res / "values-es" / "strings.xml")):
        _, parsed, err = run_cli(slint_main, ["--json", str(target)])
        rc, _, err2 = run_cli(slint_main, ["--strict", str(target)])
        android[name] = {"findings": sum(len(fs) for locs in (parsed or {}).values() for fs in locs.values()),
                         "strict_rc": rc, "error": err or err2}
    android_entries = len(list(extract(res / "values-es" / "strings.xml")))

    out_rows, groups = summarise(rows, api, po)
    preds, flagged, agree = predictions(groups, out_rows, android, xliff_drift)
    meta = {"slint_blind_version": VERSION, "slint_version": version("i18n-security-lint"),
            "rows_commit": ROWS_URL.split("/")[-3], "rows": len(rows), "po_errors": errors,
            "xliff_entries": xliff_entries, "xliff_drift_findings": xliff_drift, "xliff_error": xerr,
            "android_extract_entries": android_entries, "android": android, "api_flagged": flagged,
            "po_agrees_with_api": agree}
    unseen = sorted((e for e in out_rows if e["slint_api"] != "flagged"),
                    key=lambda e: (e["use"] != "formatted", e["kind"], e["app"], e["locale"], e["key"]))

    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "slint_blind.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "groups": groups,
                   "predictions": [{"id": p, "text": t, "held": ok} for p, t, ok in preds]},
                  f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out_dir, "slint_blind_rows.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    text = report(meta, groups, preds, android, xliff_drift, unseen)
    with open(os.path.join(a.out_dir, "slint_blind.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print("slint: %d rows, api flagged %d, po agrees %d, po errors %d, xliff entries %d drift %d, "
          "android extract entries %d" % (len(rows), flagged, agree, len(errors), xliff_entries, xliff_drift,
                                          android_entries))
    for pid, t, ok in preds:
        print("%s %s: %s" % (pid, "HELD" if ok else "FAILED", t))


if __name__ == "__main__":
    main()
