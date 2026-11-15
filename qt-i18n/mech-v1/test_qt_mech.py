# Tests for qt_mech.py (no Qt needed). Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import struct
import unittest

import qt_l10n
import qt_mech as m


class ElfHash(unittest.TestCase):
    def test_small(self):
        self.assertEqual(m.elf_hash(b""), 1)
        self.assertEqual(m.elf_hash(b"A"), 0x41)
        self.assertEqual(m.elf_hash(b"AB"), 0x452)

    def test_range(self):
        h = m.elf_hash(b"\xff" * 40)
        self.assertTrue(0 < h < 2 ** 32)
        self.assertEqual(h & 0xF0000000, 0)


class QmBytes(unittest.TestCase):
    def test_layout(self):
        b = m.qm_bytes("Mech", "Hello", "Hallo")
        self.assertEqual(b[:16], m.QM_MAGIC)
        self.assertEqual(b[16], m.TAG_HASHES)
        self.assertEqual(struct.unpack(">I", b[17:21])[0], 8)
        h, off = struct.unpack(">II", b[21:29])
        self.assertEqual(h, m.elf_hash(b"Hello"))
        self.assertEqual(off, 0)
        self.assertEqual(b[29], m.TAG_MESSAGES)
        n = struct.unpack(">I", b[30:34])[0]
        msg = b[34:]
        self.assertEqual(len(msg), n)
        self.assertEqual(msg[0], 3)
        tl = struct.unpack(">I", msg[1:5])[0]
        self.assertEqual(msg[5:5 + tl].decode("utf-16-be"), "Hallo")
        rest = msg[5 + tl:]
        self.assertEqual(rest[0], 6)
        sl = struct.unpack(">I", rest[1:5])[0]
        self.assertEqual(rest[5:5 + sl], b"Hello")
        rest = rest[5 + sl:]
        self.assertEqual(rest[0], 7)
        cl = struct.unpack(">I", rest[1:5])[0]
        self.assertEqual(rest[5:5 + cl], b"Mech")
        self.assertEqual(rest[5 + cl:], b"\x01")


class Grid(unittest.TestCase):
    def test_all_codes_parse(self):
        for c in m.CODES:
            self.assertIsNotNone(qt_l10n.parse_code(c), c)

    def test_sets_in_grid(self):
        cells = {(c, s) for c in m.CODES for s in m.STYLES}
        for p in m.CONTROLS + m.M1 + m.M2 + m.M3 + sorted(m.EXPLORATORY):
            self.assertIn(p, cells)
        for p in m.CONTROLS + m.M1 + m.M2 + m.M3:
            self.assertNotIn(p, m.EXPLORATORY)

    def test_checker_predictions_frozen(self):
        # The pre-registered predictions are exactly the checker's verdicts.
        for p in m.CONTROLS + m.M2:
            self.assertTrue(m.predicted_reachable(*p), p)
        for p in m.M1 + m.M3:
            self.assertFalse(m.predicted_reachable(*p), p)
        self.assertEqual(qt_l10n.judge("pt_br", "A")[0], "case")
        self.assertEqual(qt_l10n.judge("zh_Hans", "A")[0], "script_code")
        self.assertEqual(qt_l10n.judge("no", "A")[0], "legacy_code")
        self.assertEqual(qt_l10n.judge("pt-BR", "B")[0], "hyphen")
        self.assertEqual(qt_l10n.judge("sr@latin", "B")[0], "modifier")
        self.assertEqual(qt_l10n.judge("pt_BR", "A2")[0], "region_code")

    def test_code_language(self):
        self.assertEqual(m.code_language("sr@latin"), "sr")
        self.assertEqual(m.code_language("pt-BR"), "pt")
        self.assertEqual(m.code_language("zh_Hans"), "zh")


class Grade(unittest.TestCase):
    def predicted_cells(self):
        return {(c, s): m.predicted_reachable(c, s) for c in m.CODES for s in m.STYLES}

    def test_all_hold_when_qt_matches_checker(self):
        v = m.grade(self.predicted_cells())
        self.assertTrue(v["ALL"])
        self.assertEqual(v["K_cells"], len(m.CODES) * len(m.STYLES) - len(m.EXPLORATORY))
        self.assertEqual(v["K_disagreements"], [])

    def test_exploratory_does_not_break_k(self):
        cells = self.predicted_cells()
        cells[("no", "B")] = not cells[("no", "B")]
        v = m.grade(cells)
        self.assertTrue(v["K"])
        self.assertEqual(v["exploratory_disagreements"], ["no/B"])

    def test_disagreement_breaks_k_and_m(self):
        cells = self.predicted_cells()
        cells[("pt_br", "A")] = True
        v = m.grade(cells)
        self.assertFalse(v["K"])
        self.assertFalse(v["M1"])
        self.assertFalse(v["ALL"])
        self.assertEqual(v["K_disagreements"], ["pt_br/A"])

    def test_control_failure(self):
        cells = self.predicted_cells()
        cells[("de", "A")] = False
        self.assertFalse(m.grade(cells)["C"])


class TsText(unittest.TestCase):
    def test_ts(self):
        t = m.ts_text("MV2-QT-MECH de")
        self.assertIn("<name>Mech</name>", t)
        self.assertIn("<translation>MV2-QT-MECH de</translation>", t)
        self.assertTrue(t.startswith("<?xml"))


if __name__ == "__main__":
    unittest.main()
