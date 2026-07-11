"""utils/text.py — narx ajratish va formatlash testlari."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime  # noqa: E402

from utils.text import (  # noqa: E402
    fmt_amount, parse_price, parse_item_line, parse_items, truncate, parse_when,
)
from locales import TEXTS, FALLBACK_LANG  # noqa: E402


class TextTest(unittest.TestCase):
    def test_fmt_amount(self):
        self.assertEqual(fmt_amount(0), "0")
        self.assertEqual(fmt_amount(5000), "5 000")
        self.assertEqual(fmt_amount(12345678), "12 345 678")

    def test_parse_price(self):
        self.assertEqual(parse_price("12000"), 12000)
        self.assertEqual(parse_price("12 000"), 12000)
        self.assertEqual(parse_price("12.000 so'm"), 12000)
        self.assertEqual(parse_price("85 ming"), 85000)
        self.assertEqual(parse_price("85 минг сўм"), 85000)
        self.assertEqual(parse_price("12k"), 12000)
        self.assertEqual(parse_price("1,5 ming"), 1500)
        self.assertEqual(parse_price("2 mln"), 2000000)
        self.assertIsNone(parse_price("abc"))
        self.assertIsNone(parse_price(""))
        self.assertIsNone(parse_price("0"))

    def test_parse_item_line_with_price(self):
        self.assertEqual(parse_item_line("Non 5000"), ("Non", 5000, 1))
        self.assertEqual(parse_item_line("Go'sht - 85 000"), ("Go'sht", 85000, 1))
        self.assertEqual(parse_item_line("Sut: 12.000"), ("Sut", 12000, 1))
        self.assertEqual(parse_item_line("Go'sht 85 ming"), ("Go'sht", 85000, 1))
        self.assertEqual(parse_item_line("Мясо 85 тыс"), ("Мясо", 85000, 1))
        self.assertEqual(parse_item_line("Ekmek 85 bin"), ("Ekmek", 85000, 1))
        self.assertEqual(parse_item_line("Sok 12k"), ("Sok", 12000, 1))
        self.assertEqual(parse_item_line("Non 5000 so'm"), ("Non", 5000, 1))
        self.assertEqual(parse_item_line("non 5 kg 12000"), ("non 5 kg", 12000, 1))

    def test_parse_item_line_quantity_stays_in_name(self):
        # 100 dan kichik yolg'iz son — miqdor belgisisiz nomda qoladi
        self.assertEqual(parse_item_line("Olma 3"), ("Olma 3", None, 1))
        self.assertEqual(parse_item_line("Kolbasa 2 kg"), ("Kolbasa 2 kg", None, 1))
        # lekin «ming»/«so'm» bilan kelsa — aniq narx
        self.assertEqual(parse_item_line("Olma 3 ming"), ("Olma", 3000, 1))
        self.assertEqual(parse_item_line("Tuxum 90 so'm"), ("Tuxum", 90, 1))

    def test_parse_item_line_qty(self):
        # x/× belgisi yoki "ta/dona" bilan yozilgan miqdor ajratiladi
        self.assertEqual(parse_item_line("Non x2"), ("Non", None, 2))
        self.assertEqual(parse_item_line("Non ×3"), ("Non", None, 3))
        self.assertEqual(parse_item_line("Non x2 5000"), ("Non", 5000, 2))
        self.assertEqual(parse_item_line("Sut 2 ta 12000"), ("Sut", 12000, 2))
        self.assertEqual(parse_item_line("Tuxum 10 dona"), ("Tuxum", None, 10))
        # x1 — miqdor ko'rsatilmaydi
        self.assertEqual(parse_item_line("Non x1"), ("Non", None, 1))

    def test_parse_item_line_plain(self):
        self.assertEqual(parse_item_line("Guruch"), ("Guruch", None, 1))
        self.assertIsNone(parse_item_line("   "))

    def test_parse_items_multiline(self):
        items = parse_items("Non 5000\n\nSut 12000\nGuruch\n")
        self.assertEqual(items, [("Non", 5000, 1), ("Sut", 12000, 1), ("Guruch", None, 1)])

    def test_truncate(self):
        self.assertEqual(truncate("qisqa", 10), "qisqa")
        self.assertEqual(truncate("a" * 20, 10), "a" * 9 + "…")

    def test_parse_when_time_only(self):
        now = datetime(2026, 7, 11, 12, 0)
        self.assertEqual(parse_when("18:30", now), datetime(2026, 7, 11, 18, 30))
        # o'tgan vaqt — ertaga
        self.assertEqual(parse_when("09:00", now), datetime(2026, 7, 12, 9, 0))

    def test_parse_when_with_date(self):
        now = datetime(2026, 7, 11, 12, 0)
        self.assertEqual(parse_when("15.07 09:00", now), datetime(2026, 7, 15, 9, 0))
        # o'tgan sana — kelasi yil
        self.assertEqual(parse_when("01.03 10:00", now), datetime(2027, 3, 1, 10, 0))

    def test_parse_when_bad(self):
        now = datetime(2026, 7, 11, 12, 0)
        self.assertIsNone(parse_when("ertaga", now))
        self.assertIsNone(parse_when("25:70", now))
        self.assertIsNone(parse_when("32.13 10:00", now))
        self.assertIsNone(parse_when("", now))

    def test_locales_have_same_keys(self):
        """Har bir tilda inglizchadagi barcha kalitlar bo'lishi shart."""
        base = set(TEXTS[FALLBACK_LANG])
        for lang, texts in TEXTS.items():
            missing = base - set(texts)
            extra = set(texts) - base
            self.assertFalse(missing, f"{lang}: yetishmaydi {missing}")
            self.assertFalse(extra, f"{lang}: ortiqcha {extra}")

    def test_locales_placeholders_match(self):
        """{name} kabi o'rin egalari barcha tillarda bir xil bo'lishi kerak."""
        import string
        fmt = string.Formatter()

        def placeholders(s):
            return {fname for _, fname, _, _ in fmt.parse(s) if fname}

        for key, base_text in TEXTS[FALLBACK_LANG].items():
            base_ph = placeholders(base_text)
            for lang, texts in TEXTS.items():
                self.assertEqual(
                    placeholders(texts[key]), base_ph,
                    f"{lang}.{key}: o'rin egalari mos emas",
                )


if __name__ == "__main__":
    unittest.main()
