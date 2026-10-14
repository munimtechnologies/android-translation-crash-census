#!/usr/bin/env python3
"""Gets git and a JDK into the sealed census container: apt-get when the
image has it, else Eclipse Temurin's JDK unpacked under --data-dir (kept for
later runs with the same data key). Never fails the job; census.py reports
what is missing.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import glob
import os
import shutil
import subprocess
import tarfile
import urllib.request

TEMURIN = "https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jdk/hotspot/normal/eclipse"


def find_javac(data_dir):
    found = shutil.which("javac")
    if found:
        return found
    hits = sorted(glob.glob(os.path.join(data_dir, "jdk", "*", "bin", "javac")))
    return hits[-1] if hits else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/data")
    args = parser.parse_args()
    need = [pkg for pkg, exe in (("git", "git"), ("default-jdk-headless", "javac"),
                                 ("ca-certificates", None)) if exe is None or not shutil.which(exe)]
    if (shutil.which("apt-get") and (not shutil.which("git") or not shutil.which("javac"))):
        env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
        subprocess.run(["apt-get", "update", "-q"], env=env, check=False)
        subprocess.run(["apt-get", "install", "-y", "-q", "--no-install-recommends"] + need,
                       env=env, check=False)
    if not find_javac(args.data_dir):
        target = os.path.join(args.data_dir, "jdk")
        os.makedirs(target, exist_ok=True)
        archive = os.path.join(target, "temurin.tar.gz")
        try:
            print("downloading %s" % TEMURIN, flush=True)
            urllib.request.urlretrieve(TEMURIN, archive)
            with tarfile.open(archive) as tar:
                tar.extractall(target, filter="tar")
            os.remove(archive)
        except Exception as exc:  # report and carry on; census.py runs static-only
            print("JDK download failed: %s" % exc, flush=True)
    print("git: %s" % shutil.which("git"))
    print("javac: %s" % find_javac(args.data_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
