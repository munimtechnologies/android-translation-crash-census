# docu-i18n census v1, mechanism check M: what a real `docusaurus build` (pinned version, on
# Linux, where file names are case-sensitive) does with each kind of i18n folder.
#
# Builds one tiny site whose only page is src/pages/index.md (text MARKER-EN-7Q) and whose
# config lists en, fr, zh-CN, pt-BR and ja (ja with localeConfigs path 'japanese'). Translated
# copies of the page sit in i18n/fr (exact name: control K), i18n/japanese (localeConfigs
# path: control K2), i18n/zh-cn (case variant of zh-CN: W1), i18n/pt_BR (separator variant
# of pt-BR: W2) and i18n/de (not listed: W3). Writes <out>/mech.json. Always exits 0, so the
# census step after it still runs; a broken build is recorded as NOT TESTABLE.
# Usage: python3 -B mech.py <out folder>
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import json
import os
import subprocess
import sys
import tempfile
import time

VERSION = "3.10.2"
MARK = {"en": "MARKER-EN-7Q", "fr": "MARKER-FR-7Q", "zh-cn": "MARKER-ZH-7Q",
        "pt_BR": "MARKER-PT-7Q", "japanese": "MARKER-JA-7Q", "de": "MARKER-DE-7Q"}

CONFIG = """module.exports = {
  title: 'Mechanism check',
  url: 'https://example.com',
  baseUrl: '/',
  onBrokenLinks: 'warn',
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'fr', 'zh-CN', 'pt-BR', 'ja'],
    localeConfigs: {ja: {path: 'japanese'}},
  },
  presets: [['classic', {docs: false, blog: false}]],
};
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def tail(text, n=15):
    return "\n".join((text or "").strip().splitlines()[-n:])


def site(root):
    pkg = {"name": "docu-mech", "private": True,
           "dependencies": {"@docusaurus/core": VERSION, "@docusaurus/preset-classic": VERSION,
                            "react": "^19.0.0", "react-dom": "^19.0.0"}}
    write(os.path.join(root, "package.json"), json.dumps(pkg, indent=1) + "\n")
    write(os.path.join(root, "docusaurus.config.js"), CONFIG)
    write(os.path.join(root, "src", "pages", "index.md"),
          "# Mechanism page\n\n" + MARK["en"] + "\n")
    for folder, mark in MARK.items():
        if folder == "en":
            continue
        write(os.path.join(root, "i18n", folder, "docusaurus-plugin-content-pages", "index.md"),
              "# Translated page\n\n" + mark + "\n")


def scan(build):
    hits = {m: [] for m in MARK.values()}
    for dp, _, files in os.walk(build):
        for f in files:
            if not f.endswith(".html"):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, build).replace(os.sep, "/")
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for m in hits:
                if m in text:
                    hits[m].append(rel)
    return {m: sorted(v) for m, v in hits.items()}


def verdicts(build, hits):
    def has(rel, m):
        return rel in hits[MARK[m]]

    def exists(rel):
        return os.path.exists(os.path.join(build, *rel.split("/")))

    v = {}
    v["K"] = "HELD" if has("fr/index.html", "fr") else "FAILED"
    v["K2"] = "HELD" if has("ja/index.html", "japanese") else "FAILED"
    v["W1"] = ("HELD" if exists("zh-CN/index.html") and not hits[MARK["zh-cn"]]
               and has("zh-CN/index.html", "en") else "FAILED")
    v["W2"] = ("HELD" if exists("pt-BR/index.html") and not hits[MARK["pt_BR"]]
               and has("pt-BR/index.html", "en") else "FAILED")
    v["W3"] = "HELD" if not hits[MARK["de"]] and not exists("de") else "FAILED"
    return v


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/out"
    os.makedirs(out, exist_ok=True)
    res = {"docusaurus": VERSION, "verdicts": {}, "steps": {}}
    try:
        root = tempfile.mkdtemp(prefix="docu-mech-")
        site(root)
        env = dict(os.environ, CI="true", DOCUSAURUS_TELEMETRY="0", NODE_OPTIONS=
                   "--max-old-space-size=2048")
        for name, cmd, limit in (
                ("node", ["node", "--version"], 60),
                ("install", ["npm", "install", "--no-audit", "--no-fund", "--loglevel=error"],
                 1800),
                ("versions", ["npm", "ls", "@docusaurus/core", "react", "--depth=0"], 120),
                ("build", [os.path.join(root, "node_modules", ".bin", "docusaurus"), "build"],
                 1800)):
            t0 = time.time()
            p = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True,
                               errors="replace", timeout=limit)
            res["steps"][name] = {"exit": p.returncode, "seconds": round(time.time() - t0),
                                  "stdout_tail": tail(p.stdout), "stderr_tail": tail(p.stderr)}
            print("%s exit %d" % (name, p.returncode), flush=True)
            if p.returncode != 0 and name in ("install", "build"):
                raise RuntimeError("%s failed" % name)
        build = os.path.join(root, "build")
        hits = scan(build)
        res["hits"] = hits
        res["verdicts"] = verdicts(build, hits)
        res["build_dirs"] = sorted(d for d in os.listdir(build)
                                   if os.path.isdir(os.path.join(build, d)))
    except Exception as exc:  # record and keep the job going
        res["error"] = repr(exc)[:400]
        for k in ("K", "K2", "W1", "W2", "W3"):
            res["verdicts"].setdefault(k, "NOT TESTABLE (build did not finish)")
    with open(os.path.join(out, "mech.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(res["verdicts"], sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
