# Fetches census v2's code (xcode-lproj-v2/xcode_lproj_v2.py) unchanged from the public census
# repository, so v3 reuses exactly the project-file and .strings readers that produced v2's
# results. If the file is not byte-identical to the one the v2 job ran (sha256 below), it says
# so here and xcode_lproj_v3.py records it in summary.json ("v2_code_identical": false).
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import hashlib
import urllib.request

URL = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
       "main/xcode-lproj-v2/xcode_lproj_v2.py")
SHA256 = "982fdafd9eea92d185a7b5bb4b3f059bb4c8c81c393cc494f9614f437d6d9fa4"

req = urllib.request.Request(URL, headers={"User-Agent": "xcode-lproj-v3 (MV2, Munim, Inc.)"})
data = urllib.request.urlopen(req, timeout=120).read()
got = hashlib.sha256(data).hexdigest()
print("xcode_lproj_v2.py sha256", got, len(data), "bytes")
print("identical to the file the v2 job ran:", got == SHA256)
with open("xcode_lproj_v2.py", "wb") as fh:
    fh.write(data)
