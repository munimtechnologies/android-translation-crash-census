#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Store-listing language keys in F-Droid's published index that no phone can select (pre-registered).

fdroidserver copies every localized store-listing folder name (fastlane/metadata/android/<locale>/,
metadata/<appid>/<locale>/, Triple-T folders) into the repository index as-is: the only filter is a
glob that wants two lowercase letters first. The F-Droid client then picks the text whose key best
matches the phone's languages, falling back to en-US, en, then the first entry. A key such as
"jp", "cn" or "zh-rCN" is therefore published but can never be matched by language.

This script downloads F-Droid's index-v2.json (and, for comparison only, IzzyOnDroid's), reads every
locale key of every localized field (name, summary, description, video, icon, graphics, screenshots,
and the whatsNew of every version), and checks each key against BCP 47 (RFC 5646) and the IANA
Language Subtag Registry:

  valid                  well-formed, every subtag registered (deprecated ones such as iw count)
  android-r              Android resource style: zh-rCN, pt-rBR, b+sr+Latn
  underscore             would be valid with '-' instead of '_': pt_BR, zh_Hans
  unregistered-language  well-formed, but the language subtag is not a language: jp, cn, cz, ua
  unregistered-subtag    language registered, a script, region or variant is not: en-UK
  malformed              anything else

See PREREG.md for the predictions and how they are graded. Made with AI agents by MV2 of Munim,
Inc. Standard library only.
"""
import argparse
import collections
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.request

VERSION = "0.1.0"
BASE = "https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/main/"
PREREG_URL = BASE + "listing-codes/PREREG.md"
PREREG_MARK = "listing-codes census PREREG v1"
REGISTRY_URL = "https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry"
INDEXES = (("fdroid", "https://f-droid.org/repo/index-v2.json"),
           ("izzyondroid", "https://apt.izzysoft.de/fdroid/repo/index-v2.json"))
SELFTEST_PACKAGE = "org.fdroid.fdroid"
UA = "listing-codes/0.1.0 (MV2 of Munim, Inc.; mv2@munimtech.com)"

# Pre-registered thresholds (PREREG.md). Integers only.
GATE_PACKAGES = 3000
GATE_LANGUAGES = 8000
K1_LO_PER_MILLE = 5      # 0.5 %
K1_HI_PER_MILLE = 60     # 6.0 %
K2_MIN_PACKAGES = 8
K3_MIN_PACKAGES = 4
SAMPLE_SIZE = 20
H1_MIN_CHECKED = 8

LOCALIZED_META = ("name", "summary", "description", "video", "icon", "featureGraphic",
                  "promoGraphic", "tvBanner")
SAMPLE_CLASSES = ("android-r", "underscore", "unregistered-language")
CLASSES = ("valid", "android-r", "underscore", "unregistered-language", "unregistered-subtag",
           "malformed")

# Country codes and other non-language codes used for a language, and the language meant
# (the same list as l10n-guard's locale-code warning).
MEANT = {"cn": "zh", "cz": "cs", "ua": "uk", "jp": "ja", "by": "be", "dk": "da", "gr": "el",
         "sp": "es", "du": "nl", "vn": "vi", "al": "sq", "ir": "fa", "il": "he", "hk": "zh",
         "us": "en", "gb": "en", "pk": "ur", "ge": "ka", "mx": "es", "rs": "sr", "kz": "kk"}
# Registered codes that are often used for another language (exploratory only).
SUSPECT = {"kr": "ko (kr is Kanuri)", "se": "sv (se is Northern Sami)",
           "ee": "et (ee is Ewe)", "ch": "zh or de-CH (ch is Chamorro)"}
# Deprecated codes the Android platform still uses, folded for the K3 language comparison.
FOLD = {"iw": "he", "in": "id", "ji": "yi", "jw": "jv", "mo": "ro"}

LANGTAG = re.compile(r"""^
    (?P<language>[a-z]{2,3}(?:-[a-z]{3}){0,3}|[a-z]{4}|[a-z]{5,8})
    (?:-(?P<script>[a-z]{4}))?
    (?:-(?P<region>[a-z]{2}|[0-9]{3}))?
    (?P<variants>(?:-(?:[a-z0-9]{5,8}|[0-9][a-z0-9]{3}))*)
    (?P<extensions>(?:-[0-9a-wyz](?:-[a-z0-9]{2,8})+)*)
    (?P<private>-x(?:-[a-z0-9]{1,8})+)?
    $""", re.X | re.I)
PRIVATEUSE = re.compile(r"^x(?:-[a-z0-9]{1,8})+$", re.I)
ANDROID_R = re.compile(r"^(?P<language>[a-zA-Z]{2,3})-r(?:[A-Z]{2}|[0-9]{3})$")
ANDROID_B = re.compile(r"^b\+(?P<language>[a-zA-Z]{2,3})(?:\+[a-zA-Z0-9]{1,8})*$")


class Registry:
    """The subtags of the IANA Language Subtag Registry, lower-cased."""

    def __init__(self, text):
        self.date = ""
        self.subtags = collections.defaultdict(set)   # type -> {subtag}
        self.ranges = collections.defaultdict(list)   # type -> [(lo, hi)]
        self.tags = set()                             # grandfathered and redundant tags
        for rec in text.split("\n%%"):
            fields = {}
            last = None
            for line in rec.splitlines():
                if line.startswith(" ") and last:
                    fields[last] += " " + line.strip()
                elif ":" in line:
                    k, v = line.split(":", 1)
                    last = k.strip()
                    fields.setdefault(last, v.strip())
            if "File-Date" in fields:
                self.date = fields["File-Date"]
            typ = fields.get("Type")
            if not typ:
                continue
            if "Tag" in fields:
                self.tags.add(fields["Tag"].lower())
            elif "Subtag" in fields:
                s = fields["Subtag"].lower()
                if ".." in s:
                    lo, hi = s.split("..", 1)
                    self.ranges[typ].append((lo, hi))
                else:
                    self.subtags[typ].add(s)

    def has(self, typ, subtag):
        s = subtag.lower()
        if s in self.subtags[typ]:
            return True
        return any(len(lo) == len(s) and lo <= s <= hi for lo, hi in self.ranges[typ])

    def count(self, typ):
        return len(self.subtags[typ]) + len(self.ranges[typ])


def _registered(m, reg):
    """(language registered, every other subtag registered) of a LANGTAG match."""
    parts = m.group("language").split("-")
    lang_ok = reg.has("language", parts[0])
    rest_ok = all(reg.has("extlang", e) for e in parts[1:])
    if m.group("script"):
        rest_ok = rest_ok and reg.has("script", m.group("script"))
    if m.group("region"):
        rest_ok = rest_ok and reg.has("region", m.group("region"))
    for v in (m.group("variants") or "").split("-"):
        if v:
            rest_ok = rest_ok and reg.has("variant", v)
    return lang_ok, rest_ok


def classify(key, reg):
    """The class of one locale key (see the module docstring)."""
    k = key.strip()
    if k != key or not k:
        return "malformed"
    if k.lower() in reg.tags or PRIVATEUSE.match(k):
        return "valid"
    m = LANGTAG.match(k)
    if m:
        lang_ok, rest_ok = _registered(m, reg)
        if lang_ok and rest_ok:
            return "valid"
    if ANDROID_R.match(k) or ANDROID_B.match(k):
        return "android-r"
    if "_" in k:
        if classify(k.replace("_", "-"), reg) == "valid":
            return "underscore"
    if m:
        return "unregistered-subtag" if lang_ok else "unregistered-language"
    return "malformed"


def language_of(key):
    """The lower-cased language a key names, read loosely (for K3 and the exploratory tables)."""
    k = key.strip()
    for pat in (ANDROID_R, ANDROID_B):
        m = pat.match(k)
        if m:
            return m.group("language").lower()
    return re.split(r"[-_+]", k)[0].lower()


def canonical_case(key):
    """Whether a valid key is written in the canonical case (lang lower, Script, REGION)."""
    parts = key.split("-")
    for i, p in enumerate(parts):
        if i == 0:
            if p != p.lower():
                return False
        elif len(p) == 4 and p.isalpha() and i == 1:
            if p != p.title():
                return False
        elif len(p) == 2 and p.isalpha():
            if p != p.upper():
                return False
        elif p != p.lower() and not (len(p) == 4 and p.isalpha()):
            return False
    return True


def field_maps(pkg):
    """[(field name, {locale: value})] of one index-v2 package entry."""
    out = []
    meta = pkg.get("metadata") or {}
    for f in LOCALIZED_META:
        v = meta.get(f)
        if isinstance(v, dict) and v:
            out.append((f, v))
    shots = meta.get("screenshots")
    if isinstance(shots, dict):
        for kind in sorted(shots):
            v = shots[kind]
            if isinstance(v, dict) and v:
                out.append(("screenshots." + kind, v))
    versions = pkg.get("versions") or {}
    whats = {}
    for vid in sorted(versions):
        v = versions[vid] or {}
        wn = v.get("whatsNew")
        if isinstance(wn, dict):
            for loc, text in wn.items():
                whats.setdefault(loc, text)
    if whats:
        out.append(("whatsNew", whats))
    return out


def _text(v):
    if isinstance(v, str):
        return v
    return ""


def excerpt(fields, key, n=300):
    """The first n characters of the key's text: description, summary, whatsNew, then name."""
    by = dict(fields)
    for f in ("description", "summary", "whatsNew", "name"):
        t = _text((by.get(f) or {}).get(key))
        if t.strip():
            return " ".join(t.split())[:n], f
    return "", ""


def scan_index(index, reg):
    """Per-package rows of every key that is not valid, plus counts over all keys."""
    packages = index.get("packages") or {}
    key_pkgs = collections.Counter()      # key -> packages using it
    rows = []
    stats = collections.Counter()
    noncanonical = collections.Counter()
    for pid in sorted(packages):
        fields = field_maps(packages[pid] or {})
        keys = sorted({k for _, m in fields for k in m})
        stats["packages"] += 1
        if any(k not in ("en-US", "en") for k in keys):
            stats["packages_localized"] += 1
        valid_langs = set()
        cls = {}
        for k in keys:
            key_pkgs[k] += 1
            c = classify(k, reg)
            cls[k] = c
            if c == "valid":
                valid_langs.add(FOLD.get(language_of(k), language_of(k)))
                if not canonical_case(k):
                    noncanonical[k] += 1
        for k in keys:
            c = cls[k]
            if c == "valid":
                continue
            in_fields = [f for f, m in fields if k in m]
            reach = []
            for f, m in fields:
                if k not in m:
                    continue
                if len(m) == 1:
                    reach.append("only-key")
                elif "en-US" in m or "en" in m:
                    reach.append("fallback-en")
                else:
                    reach.append("no-en")
            lang = language_of(k)
            meant = MEANT.get(lang, "") if c == "unregistered-language" else (
                FOLD.get(lang, lang) if c in ("android-r", "underscore") else "")
            text, text_field = excerpt(fields, k)
            en_text, _ = excerpt(fields, "en-US")
            rows.append({
                "package": pid, "key": k, "class": c, "language": lang, "meant": meant,
                "meant_has_valid_key": ("" if not meant else
                                        ("yes" if meant in valid_langs else "no")),
                "fields": " ".join(in_fields), "reach": " ".join(sorted(set(reach))),
                "same_as_en": "yes" if text and en_text and text == en_text else "no",
                "text_field": text_field, "text": text, "en_text": en_text[:120]})
    return rows, key_pkgs, stats, noncanonical


def class_packages(rows):
    """{class: number of packages with at least one key of that class}."""
    by = collections.defaultdict(set)
    for r in rows:
        by[r["class"]].add(r["package"])
    return {c: len(by[c]) for c in CLASSES if c != "valid"}


def k3_counts(rows):
    """(packages with an unregistered-language key whose meant language is known, those where at
    least one such key's language has no valid key in the package)."""
    known, lost = set(), set()
    for r in rows:
        if r["class"] == "unregistered-language" and r["meant"]:
            known.add(r["package"])
            if r["meant_has_valid_key"] == "no":
                lost.add(r["package"])
    return len(known), len(lost)


def sample_key(pkg, key):
    return hashlib.sha256(("listing-codes v1|%s|%s" % (pkg, key)).encode("utf-8")).hexdigest()


def draw_sample(rows):
    """Per package the sample-class key with the lowest hash, then the first 20 by hash."""
    by = collections.defaultdict(list)
    for r in rows:
        if r["class"] in SAMPLE_CLASSES:
            by[r["package"]].append(r)
    kept = [min(rs, key=lambda r: sample_key(r["package"], r["key"])) for _, rs in sorted(by.items())]
    kept.sort(key=lambda r: sample_key(r["package"], r["key"]))
    return kept[:SAMPLE_SIZE]


def grade(n_packages, n_languages, rows):
    """Pre-registered verdicts K1-K4 (H1 is graded by hand). Integers only."""
    preds = ("K1", "K2", "K3", "K4")
    if n_packages < GATE_PACKAGES or n_languages < GATE_LANGUAGES:
        return {p: "NOT TESTABLE (gate: %d packages, %d languages)" % (n_packages, n_languages)
                for p in preds}
    invalid_pkgs = len({r["package"] for r in rows})
    per = class_packages(rows)
    v = {}
    v["K1"] = ("HELD" if K1_LO_PER_MILLE * n_packages <= invalid_pkgs * 1000
               <= K1_HI_PER_MILLE * n_packages else "FAILED")
    v["K2"] = "HELD" if per["unregistered-language"] >= K2_MIN_PACKAGES else "FAILED"
    known, lost = k3_counts(rows)
    if known < K3_MIN_PACKAGES:
        v["K3"] = "NOT TESTABLE (%d packages)" % known
    else:
        v["K3"] = "HELD" if lost * 2 >= known else "FAILED"
    if not invalid_pkgs:
        v["K4"] = "NOT TESTABLE (no invalid keys)"
    else:
        others = [n for c, n in per.items() if c != "android-r"]
        v["K4"] = "HELD" if per["android-r"] > max(others) else "FAILED"
    return v


def grade_h1(labels):
    """labels: hand labels of the sample rows ('translation', 'english', 'empty', 'other')."""
    checked = [x for x in labels if x]
    if len(checked) < H1_MIN_CHECKED:
        return "NOT TESTABLE"
    real = sum(1 for x in checked if x == "translation")
    return "HELD" if real * 4 >= len(checked) * 3 else "FAILED"


# Classification the real registry must reproduce before any index is read.
CONTROL = (("en-US", "valid"), ("zh-Hans-CN", "valid"), ("pt-BR", "valid"), ("iw-IL", "valid"),
           ("es-419", "valid"), ("sr-Latn", "valid"), ("fil", "valid"), ("ckb", "valid"),
           ("de-CH-1996", "valid"), ("jp", "unregistered-language"),
           ("cn", "unregistered-language"), ("zh-rCN", "android-r"), ("b+sr+Latn", "android-r"),
           ("pt_BR", "underscore"), ("zh_Hant", "underscore"), ("ja-JA", "unregistered-subtag"),
           ("zh-CN.UTF-8", "malformed"), ("kr", "valid"))


def control(reg):
    got = [(k, classify(k, reg)) for k, _ in CONTROL]
    return got == list(CONTROL), got


def fetch(url, timeout=600):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def wait_for_prereg(minutes):
    """The pre-registration must be public before any index is read."""
    end = time.time() + minutes * 60
    while True:
        try:
            text = fetch(PREREG_URL, 60).decode("utf-8")
            if PREREG_MARK in text:
                return hashlib.sha256(text.encode("utf-8")).hexdigest()
        except OSError:
            pass
        if time.time() > end:
            return None
        time.sleep(60)


ROW_COLS = ["package", "key", "class", "language", "meant", "meant_has_valid_key", "fields",
            "reach", "same_as_en", "text_field", "text", "en_text"]


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", errors="replace", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def exploratory(rows, key_pkgs, stats, noncanonical, reg):
    """Not graded: invalid keys by name, reach, suspect registered codes, case."""
    invalid_keys = collections.Counter()
    reach = collections.Counter()
    for r in rows:
        invalid_keys["%s (%s)" % (r["key"], r["class"])] += 1
        for x in r["reach"].split():
            reach["%s/%s" % (r["class"], x)] += 1
    suspect = {k: {"packages": key_pkgs.get(k, 0), "note": SUSPECT[k]} for k in sorted(SUSPECT)}
    return {"packages": stats["packages"], "packages_localized": stats["packages_localized"],
            "distinct_keys": len(key_pkgs),
            "invalid_rows": len(rows), "invalid_packages": len({r["package"] for r in rows}),
            "class_packages": class_packages(rows),
            "invalid_keys_top": dict(invalid_keys.most_common(60)),
            "reach_by_class": dict(reach),
            "unregistered_language_same_as_en": sum(1 for r in rows if r["class"] ==
                                                    "unregistered-language"
                                                    and r["same_as_en"] == "yes"),
            "suspect_registered_codes": suspect,
            "noncanonical_case_valid_keys": dict(noncanonical.most_common(40)),
            "k3_known_lost": list(k3_counts(rows))}


def run_index(name, url, reg, out_dir):
    raw = fetch(url)
    sha = hashlib.sha256(raw).hexdigest()
    index = json.loads(raw)
    del raw
    repo = index.get("repo") or {}
    rows, key_pkgs, stats, noncanon = scan_index(index, reg)
    selftest = None
    if name == "fdroid":
        pkg = (index.get("packages") or {}).get(SELFTEST_PACKAGE) or {}
        desc = ((pkg.get("metadata") or {}).get("description") or {})
        selftest = {"package": SELFTEST_PACKAGE, "description_keys": len(desc),
                    "has_en_US": "en-US" in desc}
    del index
    write_csv(os.path.join(out_dir, "%s-keys.csv" % name), ROW_COLS, rows)
    with open(os.path.join(out_dir, "%s-all-keys.csv" % name), "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "class", "packages"])
        for k in sorted(key_pkgs):
            w.writerow([k, classify(k, reg), key_pkgs[k]])
    return {"url": url, "sha256": sha, "repo_timestamp": repo.get("timestamp"),
            "rows": rows, "key_pkgs": key_pkgs, "stats": stats, "noncanon": noncanon,
            "selftest": selftest}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--prereg-wait-minutes", type=float, default=45)
    ap.add_argument("--skip-prereg-check", action="store_true")
    a = ap.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)
    started = time.time()
    print("listing_codes %s" % VERSION, flush=True)
    reg_raw = fetch(REGISTRY_URL)
    reg = Registry(reg_raw.decode("utf-8"))
    ok, got = control(reg)
    print("registry %s: %d languages; control %s" % (reg.date, reg.count("language"), ok),
          flush=True)
    if not ok:
        print("control failed: %s" % got, file=sys.stderr)
        return 6
    prereg_sha = None
    if not a.skip_prereg_check:
        prereg_sha = wait_for_prereg(a.prereg_wait_minutes)
        if not prereg_sha:
            print("PREREG.md not public; stopping before reading any index", file=sys.stderr)
            return 4
    results = {}
    for name, url in INDEXES:
        try:
            results[name] = run_index(name, url, reg, a.out_dir)
            print("%s: %d packages, %d invalid rows" % (
                name, results[name]["stats"]["packages"], len(results[name]["rows"])), flush=True)
        except Exception as e:  # the comparison index may be unavailable; F-Droid is required
            print("%s failed: %r" % (name, e), file=sys.stderr)
            if name == "fdroid":
                return 5
    fd = results["fdroid"]
    st = fd["selftest"]
    if not (st["has_en_US"] and st["description_keys"] >= 10):
        print("selftest failed: %s" % st, file=sys.stderr)
        return 3
    sample = draw_sample(fd["rows"])
    write_csv(os.path.join(a.out_dir, "sample.csv"), ["sample"] + ROW_COLS + ["label", "note"],
              [dict(r, sample=i, label="", note="") for i, r in enumerate(sample, 1)])
    verdicts = grade(fd["stats"]["packages"], reg.count("language"), fd["rows"])
    verdicts["H1"] = ("PENDING HAND CHECK (sample of %d)" % len(sample)
                      if len(sample) >= H1_MIN_CHECKED else "NOT TESTABLE (sample of %d)"
                      % len(sample))
    summary = {
        "verdicts": verdicts, "version": VERSION, "prereg_sha256": prereg_sha,
        "registry": {"url": REGISTRY_URL, "file_date": reg.date,
                     "sha256": hashlib.sha256(reg_raw).hexdigest(),
                     "languages": reg.count("language")},
        "control": True, "selftest": st, "sample_size": len(sample),
        "indexes": {n: {"url": r["url"], "sha256": r["sha256"],
                        "repo_timestamp": r["repo_timestamp"],
                        "exploratory": exploratory(r["rows"], r["key_pkgs"], r["stats"],
                                                   r["noncanon"], reg)}
                    for n, r in results.items()},
        "minutes": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w", encoding="utf-8",
              errors="replace") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(verdicts), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
