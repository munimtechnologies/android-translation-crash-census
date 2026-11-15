#!/usr/bin/env python3
# qt_mech.py: a real-Qt runtime test of which translation file names QTranslator::load reaches,
# graded against the qt-i18n desk checker (qt_l10n.judge). Pre-registered in PREREG.md.
# Needs PySide6 (QtCore). Builds .qm files with lrelease if one is found, else with a small
# writer of the .qm format; every file is checked by loading it and translating one string.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import csv
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

import qt_l10n

CONTEXT = "Mech"
SOURCE = "Hello"
MARK = "MV2-QT-MECH"

CODES = ["de", "pt_BR", "pt", "zh_CN", "zh_TW", "zh", "nb", "he", "fil", "es_419", "sr",
         "zh_Hans", "zh_Hant", "sr_Latn", "pt_br", "zh_tw", "no", "tl", "iw",
         "pt-BR", "sr@latin"]
STYLES = ["A", "A2", "B"]
CONTROLS = [("de", "A"), ("de", "A2"), ("de", "B"), ("pt_BR", "A"), ("pt_BR", "B"),
            ("zh_CN", "A"), ("zh_CN", "B")]
M1 = [(c, "A") for c in ("zh_Hans", "zh_Hant", "sr_Latn", "pt_br", "zh_tw", "no", "tl")]
M2 = [("pt_br", "B"), ("zh_tw", "B")]
M3 = [(c, s) for c in ("pt-BR", "sr@latin") for s in STYLES]
EXPLORATORY = {("no", "B"), ("tl", "B"), ("iw", "B"), ("zh_Hans", "B"), ("zh_Hant", "B"),
               ("sr_Latn", "B")}
UI_LOCALES = ["zh_CN", "zh_TW", "zh_HK", "zh_SG", "pt_BR", "pt_PT", "nb_NO", "fil_PH", "he_IL",
              "sr_RS", "sr_Latn_RS", "de_DE", "es_419"]
SYSTEM_LANGS = ["zh_CN.UTF-8", "zh_TW.UTF-8", "pt_BR.UTF-8", "nb_NO.UTF-8", "de_DE.UTF-8",
                "sr_RS.UTF-8", "sr_RS@latin.UTF-8"]

QM_MAGIC = bytes([0x3C, 0xB8, 0x64, 0x18, 0xCA, 0xEF, 0x9C, 0x95,
                  0xCD, 0x21, 0x1C, 0xBF, 0x60, 0xA1, 0xBD, 0xDD])
TAG_HASHES = 0x42
TAG_MESSAGES = 0x69


def elf_hash(data):
    """Qt's elfHash over bytes (qtranslator.cpp); never 0."""
    h = 0
    for b in data:
        h = ((h << 4) + b) & 0xFFFFFFFF
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= (~g) & 0xFFFFFFFF
    return h or 1


def qm_bytes(context, source, translation):
    """A minimal .qm file: one message, a Hashes block and a Messages block."""
    tr = translation.encode("utf-16-be")
    src = source.encode("utf-8")
    ctx = context.encode("utf-8")
    msg = (b"\x03" + struct.pack(">I", len(tr)) + tr
           + b"\x06" + struct.pack(">I", len(src)) + src
           + b"\x07" + struct.pack(">I", len(ctx)) + ctx
           + b"\x01")
    hashes = struct.pack(">II", elf_hash(src), 0)
    return (QM_MAGIC
            + bytes([TAG_HASHES]) + struct.pack(">I", len(hashes)) + hashes
            + bytes([TAG_MESSAGES]) + struct.pack(">I", len(msg)) + msg)


def ts_text(translation):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
            '<TS version="2.1" language="en">\n<context>\n    <name>%s</name>\n'
            '    <message>\n        <source>%s</source>\n'
            '        <translation>%s</translation>\n    </message>\n</context>\n</TS>\n'
            % (CONTEXT, SOURCE, translation))


def expected_text(code):
    return "%s %s" % (MARK, code)


def find_lrelease():
    for cand in ("pyside6-lrelease", "/usr/lib/qt6/bin/lrelease", "lrelease6", "lrelease"):
        path = cand if os.path.isabs(cand) and os.path.exists(cand) else shutil.which(cand)
        if path:
            return path
    return None


def code_language(code):
    return re.split(r"[_@-]", code)[0]


def predicted_reachable(code, style):
    return qt_l10n.judge(code, style) is None


def grade(cells):
    """cells: {(code, style): bool reachable}. Returns the verdict dict."""
    def all_are(pairs, want):
        return all(cells.get(p) is want for p in pairs)
    k_cells = [p for p in cells if p not in EXPLORATORY]
    disagree = sorted("%s/%s" % p for p in k_cells if cells[p] != predicted_reachable(*p))
    expl = sorted("%s/%s" % p for p in EXPLORATORY
                  if p in cells and cells[p] != predicted_reachable(*p))
    v = {
        "C": all_are(CONTROLS, True),
        "M1": all_are(M1, False),
        "M2": all_are(M2, True),
        "M3": all_are(M3, False),
        "K": not disagree and len(k_cells) == len(CODES) * len(STYLES) - len(EXPLORATORY),
        "K_disagreements": disagree,
        "K_cells": len(k_cells),
        "exploratory_disagreements": expl,
    }
    v["ALL"] = all(v[k] for k in ("C", "M1", "M2", "M3", "K"))
    return v


# ------------------------------------------------------------------ Qt side

def qt_run(out):
    from PySide6 import QtCore
    from PySide6.QtCore import QCoreApplication, QLocale, QTranslator
    app = QCoreApplication.instance() or QCoreApplication([])
    env = {"pyside6": getattr(__import__("PySide6"), "__version__", "?"),
           "qt": QtCore.qVersion(), "python": sys.version.split()[0]}
    work = tempfile.mkdtemp(prefix="qtmech-")
    lrelease = find_lrelease()
    env["lrelease"] = lrelease or ""
    env["qm_writer"] = {}
    dirs, qm_ok = {}, {}
    for i, code in enumerate(CODES):
        d = os.path.join(work, "%02d" % i)
        os.makedirs(d)
        qm = os.path.join(d, "app_%s.qm" % code)
        how = "none"
        if lrelease:
            ts = os.path.join(work, "%02d.ts" % i)
            with open(ts, "w", encoding="utf-8") as fh:
                fh.write(ts_text(expected_text(code)))
            r = subprocess.run([lrelease, ts, "-qm", qm], capture_output=True, text=True)
            if r.returncode == 0 and os.path.exists(qm):
                how = "lrelease"
        if how == "none":
            with open(qm, "wb") as fh:
                fh.write(qm_bytes(CONTEXT, SOURCE, expected_text(code)))
            how = "writer"
        t = QTranslator()
        ok = bool(t.load(qm)) and t.translate(CONTEXT, SOURCE) == expected_text(code)
        if not ok and how == "lrelease":
            with open(qm, "wb") as fh:
                fh.write(qm_bytes(CONTEXT, SOURCE, expected_text(code)))
            how = "writer"
            t = QTranslator()
            ok = bool(t.load(qm)) and t.translate(CONTEXT, SOURCE) == expected_text(code)
        env["qm_writer"][code] = how
        dirs[code] = d
        qm_ok[code] = ok
    V = all(qm_ok.values())

    any_script = QLocale.Script.AnyScript
    terr = getattr(QLocale, "Territory", None)
    any_terr = terr.AnyTerritory if terr is not None else QLocale.Country.AnyCountry
    cells, rows = {}, []
    for code in CODES:
        lang = QLocale(code_language(code)).language()
        locs = [] if lang == QLocale.Language.C else list(
            QLocale.matchingLocales(lang, any_script, any_terr))
        for style in STYLES:
            hits, content_ok = [], True
            for loc in locs:
                t = QTranslator()
                name = loc.name()
                if style == "A":
                    ok = t.load("app_" + name, dirs[code])
                elif style == "A2":
                    ok = t.load("app_" + name.split("_")[0], dirs[code])
                else:
                    ok = t.load(loc, "app", "_", dirs[code])
                if ok:
                    hits.append(loc.bcp47Name() + "(" + name + ")")
                    if t.translate(CONTEXT, SOURCE) != expected_text(code):
                        content_ok = False
            reach = bool(hits)
            cells[(code, style)] = reach
            rows.append({"code": code, "style": style, "qt_reachable": reach,
                         "checker_reachable": predicted_reachable(code, style),
                         "agree": reach == predicted_reachable(code, style),
                         "exploratory": (code, style) in EXPLORATORY,
                         "locales_tried": len(locs), "hits": len(hits),
                         "first_hits": " ".join(sorted(set(hits))[:6]),
                         "content_ok": content_ok})
    with open(os.path.join(out, "cells.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    ui = {n: list(QLocale(n).uiLanguages()) for n in UI_LOCALES}
    ui_names = {n: QLocale(n).name() for n in UI_LOCALES}
    system = {}
    child = ("from PySide6.QtCore import QLocale\nl = QLocale.system()\n"
             "print(l.name())\nprint('|'.join(l.uiLanguages()))\nprint(l.bcp47Name())\n")
    for lang in SYSTEM_LANGS:
        e = {k: v for k, v in os.environ.items()
             if not k.startswith("LC_") and k not in ("LANG", "LANGUAGE")}
        e["LANG"] = lang
        e["LC_ALL"] = lang
        r = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, env=e)
        lines = r.stdout.splitlines() + ["", "", ""]
        system[lang] = {"name": lines[0], "uiLanguages": lines[1].split("|") if lines[1] else [],
                        "bcp47": lines[2], "rc": r.returncode, "stderr": r.stderr[-300:]}
    S = all(system[l]["name"] == QLocale(l.split(".")[0]).name()
            for l in SYSTEM_LANGS if "@" not in l)
    v = grade(cells)
    v["V"] = V
    v["S"] = S
    v["ALL"] = v["ALL"] and V
    content = all(r["content_ok"] for r in rows)
    summary = {"verdicts": v, "env": env, "qm_ok": qm_ok, "content_ok": content,
               "uiLanguages": ui, "ui_names": ui_names, "system_locale": system,
               "n_cells": len(rows)}
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
    del app
    return summary


def main(argv):
    out = argv[1] if len(argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    try:
        s = qt_run(out)
        print(json.dumps(s["verdicts"], indent=1, sort_keys=True))
        print("env", json.dumps(s["env"]["pyside6"]), json.dumps(s["env"]["qt"]),
              "lrelease", json.dumps(s["env"]["lrelease"]))
    except Exception as exc:  # must-finish: record and exit 0
        import traceback
        with open(os.path.join(out, "error.txt"), "w", encoding="utf-8") as fh:
            fh.write(traceback.format_exc())
        print("ERROR", repr(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
