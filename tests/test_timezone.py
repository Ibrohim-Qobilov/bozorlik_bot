"""utils/timezone.py — vaqt mintaqasi aylantirishlari testlari."""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.timezone import (  # noqa: E402
    DEFAULT_TZ, LANG_TZ, TIMEZONES, VALID_OFFSETS,
    default_tz, to_utc, to_local, utc_str_to_local, sqlite_modifier, utc_label,
)


class TimezoneTest(unittest.TestCase):
    def test_default_tz_by_lang(self):
        self.assertEqual(default_tz("uz"), 300)   # Toshkent +5
        self.assertEqual(default_tz("tr"), 180)   # Anqara +3
        self.assertEqual(default_tz("ky"), 360)   # Bishkek +6
        self.assertEqual(default_tz("ru"), 180)   # Moskva +3
        self.assertEqual(default_tz("xx"), DEFAULT_TZ)  # noma'lum til

    def test_to_utc_local_roundtrip(self):
        local = datetime(2026, 7, 11, 18, 30)
        # +5: mahalliy 18:30 -> UTC 13:30
        self.assertEqual(to_utc(local, 300), datetime(2026, 7, 11, 13, 30))
        # UTC -> mahalliy teskari amal
        self.assertEqual(to_local(to_utc(local, 300), 300), local)

    def test_to_utc_crosses_midnight(self):
        # +6: mahalliy 02:00 -> oldingi kun UTC 20:00
        local = datetime(2026, 7, 11, 2, 0)
        self.assertEqual(to_utc(local, 360), datetime(2026, 7, 10, 20, 0))

    def test_utc_str_to_local(self):
        # UTC 13:30 -> Toshkent (+5) 18:30
        self.assertEqual(utc_str_to_local("2026-07-11 13:30", 300), "11.07 18:30")
        # kun oshib ketishi: UTC 21:00 +6 -> ertasi 03:00
        self.assertEqual(utc_str_to_local("2026-07-11 21:00", 360), "12.07 03:00")
        # buzuq satr — o'zini qaytaradi
        self.assertEqual(utc_str_to_local("xato", 300), "xato")

    def test_sqlite_modifier(self):
        self.assertEqual(sqlite_modifier(300), "+300 minutes")
        self.assertEqual(sqlite_modifier(0), "+0 minutes")
        self.assertEqual(sqlite_modifier(-180), "-180 minutes")

    def test_utc_label(self):
        self.assertEqual(utc_label(300), "UTC+5")
        self.assertEqual(utc_label(180), "UTC+3")
        self.assertEqual(utc_label(0), "UTC+0")
        self.assertEqual(utc_label(-90), "UTC-1:30")

    def test_timezones_offsets_are_valid(self):
        # Klaviaturadagi har bir siljish VALID_OFFSETS ichida bo'lishi kerak
        for minutes, label in TIMEZONES:
            self.assertIn(minutes, VALID_OFFSETS)
            self.assertTrue(label)
        # Tillar standarti ham taklif ro'yxatida bo'lsin (foydalanuvchi ko'ra oladi)
        for lang, minutes in LANG_TZ.items():
            self.assertIn(minutes, VALID_OFFSETS, f"{lang} standarti taklifda yo'q")


if __name__ == "__main__":
    unittest.main()
