"""handlers/backup.py — zaxira jadval (.xlsx) testlari.

Test o'z vaqtinchalik bazasini ishlatadi — haqiqiy `bozorlik.db` ga tegmaydi.
`handlers` paketining __init__ zanjiriga bog'lanmaslik uchun modul fayldan
to'g'ridan-to'g'ri yuklanadi (faqat backup.py va uning bevosita importlari kerak).
"""
import importlib.util
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# database import qilinishidan OLDIN muhitni sozlaymiz (config shu yerda o'qiydi).
# DB_PATH test_db bilan bir xil — config birinchi bo'lib qaysi testdan import
# qilinishidan qat'i nazar, bitta vaqtinchalik baza ishlatiladi.
os.environ["BOT_TOKEN"] = "test:token"
os.environ["DB_PATH"] = os.path.join(tempfile.gettempdir(), "bozorlik_test.db")

_spec = importlib.util.spec_from_file_location(
    "backup_module", os.path.join(_ROOT, "handlers", "backup.py")
)
backup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backup)

ITEMS = [
    {"name": "Non", "price": 5000, "bought": True},
    {"name": "Sut", "price": None, "bought": False},
    {"name": "Go'sht", "price": 85000, "bought": False},
]


class BackupXlsxTest(unittest.TestCase):
    def test_xlsx_roundtrip(self):
        """Bot yasagan .xlsx qayta o'qilganda nom, mahsulotlar va narxlar qaytadi."""
        data = backup._build_xlsx("uz", "Shanba bozorlik", ITEMS)
        self.assertEqual(data[:4], b"PK\x03\x04")  # haqiqiy zip/xlsx

        entry = backup._parse_xlsx(data)
        self.assertEqual(entry["name"], "Shanba bozorlik")
        self.assertEqual([i["name"] for i in entry["items"]], ["Non", "Sut", "Go'sht"])
        self.assertEqual([i["price"] for i in entry["items"]], [5000, None, 85000])

    def test_parse_skips_header_and_total_rows(self):
        """Sarlavha va «Jami» qatorlari mahsulot deb olinmaydi."""
        data = backup._build_xlsx("ru", "Список", [{"name": "Хлеб", "price": 3000}])
        entry = backup._parse_xlsx(data)
        self.assertEqual(len(entry["items"]), 1)
        self.assertEqual(entry["items"][0]["name"], "Хлеб")

    def test_empty_list_roundtrip(self):
        entry = backup._parse_xlsx(backup._build_xlsx("uz", "Bo'sh", []))
        self.assertEqual(entry["name"], "Bo'sh")
        self.assertEqual(entry["items"], [])

    def test_lists_table_columns(self):
        """Jadvalda № | Nomi | Summa ustunlari va qiymatlar chiqadi."""
        table = backup._lists_table("uz", [
            {"id": 7, "name": "Bozor", "total": 2, "done": 1, "sum": 250000},
            {"id": 8, "name": "Haftalik", "total": 0, "done": 0, "sum": 0},
        ])
        self.assertTrue(table.startswith("<pre>") and table.endswith("</pre>"))
        for piece in ("№", "Nomi", "Summa", "Bozor", "250 000", "—"):
            self.assertIn(piece, table)

    def test_lists_table_escapes_html(self):
        table = backup._lists_table(
            "uz", [{"id": 1, "name": "<b>xavf</b>", "total": 0, "done": 0, "sum": 0}]
        )
        self.assertNotIn("<b>", table)

    def test_safe_filename(self):
        self.assertEqual(backup._safe_filename("Shanba bozorlik", "xlsx"), "Shanba bozorlik.xlsx")
        self.assertEqual(backup._safe_filename("a/b\\c:d", "pdf"), "abcd.pdf")
        self.assertEqual(backup._safe_filename("???", "pdf"), "bozorlik.pdf")

    def test_pdf_build(self):
        """PDF yasaladi: %PDF sarlavhasi, shrift ichiga joylangani uchun hajmi katta."""
        data = backup._build_pdf("uz", "Shanba bozorlik", ITEMS)
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertGreater(len(data), 5_000)  # DejaVu shrifti ichiga joylangan

    def test_pdf_cyrillic(self):
        """Kirillcha nomlar bilan ham PDF xatosiz yasaladi."""
        data = backup._build_pdf("ru", "Субботний базар", [{"name": "Хлеб", "price": 3000}])
        self.assertTrue(data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
