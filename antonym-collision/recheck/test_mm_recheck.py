"""Tests for mm_recheck.py (Apache-2.0). Made by MV2 of Munim, Inc. with AI agents."""

import io
import json
import tarfile
import unittest

import mm_recheck as m

SRC = {
    "channel_header.delete": "Archive Channel",
    "channel_header.unarchive": "Unarchive Channel",
    "admin.unarchiveChannel": "Unarchive channel",
    "sidebar.unarchive": "Unarchive Channel...",
    "other": "Something else",
}
IT = {
    "channel_header.delete": "Archivia Canale",
    "channel_header.unarchive": "Archivia Canale",
    "admin.unarchiveChannel": "Ripristina canale",
    "sidebar.unarchive": "Ripristina canale",
    "other": "Altro",
}
OLD = {"locale": "it", "key1": "channel_header.delete", "key2": "channel_header.unarchive",
       "en1": "Archive Channel", "en2": "Unarchive Channel", "value": "Archivia Canale"}


class NormTest(unittest.TestCase):
    def test_case_space_and_trailing_punctuation(self):
        self.assertEqual(m.norm("  Unarchive   Channel... "), "unarchive channel")
        self.assertEqual(m.norm("First Name Attribute:"), "first name attribute")
        self.assertEqual(m.norm("Disabling…"), "disabling")

    def test_inner_punctuation_kept(self):
        self.assertNotEqual(m.norm("Convert to public"), m.norm("Convert to: public"))


class AlternativesTest(unittest.TestCase):
    def test_finds_other_keys_with_same_english(self):
        alts = m.alternatives(SRC, IT, "channel_header.unarchive", "Archivia Canale")
        self.assertEqual(alts, {"Ripristina canale": ["admin.unarchiveChannel", "sidebar.unarchive"]})

    def test_excludes_the_shared_value_and_the_key_itself(self):
        self.assertEqual(m.alternatives(SRC, IT, "channel_header.delete", "Archivia Canale"), {})

    def test_skips_missing_and_empty_translations(self):
        tgt = dict(IT, **{"admin.unarchiveChannel": "  "})
        del tgt["sidebar.unarchive"]
        self.assertEqual(m.alternatives(SRC, tgt, "channel_header.unarchive", "Archivia Canale"), {})

    def test_show_ranks_most_used_first(self):
        self.assertEqual(m.show({"b": ["k1"], "a": ["k2", "k3"]}), "a (k2; k3) | b (k1)")
        self.assertEqual(m.show({}), "")


class StatusTest(unittest.TestCase):
    def test_statuses(self):
        self.assertEqual(m.status("X", "X", " X "), "still")
        self.assertEqual(m.status("X", "Y", "Y"), "changed")
        self.assertEqual(m.status("X", "X", "Z"), "gone")
        self.assertEqual(m.status("X", None, "X"), "gone")
        self.assertEqual(m.status("X", "", ""), "gone")


class RecheckTest(unittest.TestCase):
    def test_still_row_gets_catalog_wording(self):
        graded = {("it", "channel_header.delete", "channel_header.unarchive"): "real"}
        rows = m.recheck([OLD], graded, {}, SRC, {"it": IT})
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["status"], r["graded"]), ("still", "real"))
        self.assertEqual(r["alt1"], "")
        self.assertEqual(r["alt2"], "Ripristina canale (admin.unarchiveChannel; sidebar.unarchive)")

    def test_gone_row_has_no_alternatives(self):
        fixed = dict(IT, **{"channel_header.unarchive": "Ripristina canale"})
        r = m.recheck([OLD], {}, {}, SRC, {"it": fixed})[0]
        self.assertEqual((r["status"], r["value2_now"], r["alt2"]), ("gone", "Ripristina canale", ""))

    def test_missing_locale_is_gone(self):
        self.assertEqual(m.recheck([OLD], {}, {}, SRC, {})[0]["status"], "gone")

    def test_new_warnings_listed_once(self):
        current = {("it", "channel_header.delete", "channel_header.unarchive"): "Archivia Canale",
                   ("it", "a", "b"): "Z"}
        rows = m.recheck([OLD], {}, current, SRC, {"it": IT})
        self.assertEqual([r["status"] for r in rows], ["still", "new"])
        self.assertEqual((rows[1]["key1"], rows[1]["value1_now"]), ("a", "Z"))


class ReadCatalogsTest(unittest.TestCase):
    def test_reads_only_webapp_i18n_json(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT,
                          pax_headers={"comment": "abc123"}) as tar:
            for name, data in (("mattermost-abc/webapp/channels/src/i18n/it.json", b'{"a": "b"}'),
                               ("mattermost-abc/webapp/channels/src/i18n/zh-TW.json", b"{}"),
                               ("mattermost-abc/server/i18n/it.json", b"{}"),
                               ("mattermost-abc/webapp/channels/src/i18n/README.md", b"x")):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        buf.seek(0)
        files, commit = m.read_catalogs(buf)
        self.assertEqual(sorted(files), ["it", "zh-TW"])
        self.assertEqual(json.loads(files["it"]), {"a": "b"})
        self.assertEqual(commit, "abc123")


if __name__ == "__main__":
    unittest.main()
