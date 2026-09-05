"""database/db.py — CRUD testlari.

Test o'z vaqtinchalik bazasini ishlatadi — haqiqiy `bozorlik.db` ga tegmaydi.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# database import qilinishidan OLDIN muhitni sozlaymiz (config shu yerda o'qiydi).
os.environ["BOT_TOKEN"] = "test:token"
_TMP_DB = os.path.join(tempfile.gettempdir(), "bozorlik_test.db")
os.environ["DB_PATH"] = _TMP_DB
os.environ["SUPABASE_DB_URL"] = ""

import database as db  # noqa: E402


class DBTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if os.path.exists(_TMP_DB):
            os.remove(_TMP_DB)  # har test uchun toza baza
        await db.init_db()

    async def test_lang_roundtrip(self):
        self.assertFalse(await db.user_exists(1))
        await db.set_lang(1, "ru")
        self.assertTrue(await db.user_exists(1))
        self.assertEqual(await db.get_lang(1), "ru")
        self.assertEqual(await db.get_lang(999), "uz")  # noma'lum foydalanuvchi

    async def test_tz_default_and_set(self):
        # o'zi tanlamagan — til bo'yicha standart siljish
        await db.set_lang(1, "tr")
        self.assertEqual(await db.get_tz(1), 180)   # Anqara +3
        await db.set_lang(2, "ky")
        self.assertEqual(await db.get_tz(2), 360)   # Bishkek +6
        self.assertEqual(await db.get_tz(999), 300)  # noma'lum -> standart (+5)
        # tanlagach — o'sha saqlanadi, til o'zgarsa ham qoladi
        await db.set_tz(1, 300)
        self.assertEqual(await db.get_tz(1), 300)
        await db.set_lang(1, "ru")  # til yangilansa ham tanlangan tz o'zgarmaydi
        self.assertEqual(await db.get_tz(1), 300)

    async def test_create_list_owner_is_member(self):
        list_id = await db.create_list(1, "Shanba bozorlik")
        lst = await db.get_list(list_id)
        self.assertEqual(lst["name"], "Shanba bozorlik")
        self.assertEqual(lst["owner_id"], 1)
        self.assertTrue(await db.is_member(list_id, 1))
        self.assertEqual(await db.count_members(list_id), 1)

    async def test_join_by_code(self):
        list_id = await db.create_list(1, "Bozor")
        code = (await db.get_list(list_id))["code"]
        lst = await db.get_list_by_code(code)
        self.assertEqual(lst["id"], list_id)
        await db.add_member(list_id, 2)
        self.assertTrue(await db.is_member(list_id, 2))
        self.assertEqual(sorted(await db.get_members(list_id)), [1, 2])
        # takror qo'shilish xato bermaydi
        await db.add_member(list_id, 2)
        self.assertEqual(await db.count_members(list_id), 2)

    async def test_items_flow(self):
        list_id = await db.create_list(1, "Bozor")
        non = await db.add_item(list_id, "Non", 5000)
        sut = await db.add_item(list_id, "Sut")
        items = await db.get_items(list_id)
        self.assertEqual([i["name"] for i in items], ["Non", "Sut"])
        self.assertEqual(items[0]["price"], 5000)
        self.assertIsNone(items[1]["price"])
        self.assertFalse(items[0]["bought"])

        await db.set_bought(non, 1)
        await db.set_bought(sut, 2, price=12000)
        items = await db.get_items(list_id)
        self.assertTrue(all(i["bought"] for i in items))
        self.assertEqual(items[1]["price"], 12000)
        spent = sum(i["price"] for i in items if i["bought"] and i["price"])
        self.assertEqual(spent, 17000)

        await db.set_unbought(non)
        item = await db.get_item(non)
        self.assertFalse(item["bought"])
        self.assertIsNone(item["bought_by"])
        self.assertEqual(item["price"], 5000)  # narx saqlanib qoladi

    async def test_user_lists_counts(self):
        a = await db.create_list(1, "A")
        await db.create_list(1, "B")
        i1 = await db.add_item(a, "Non")
        await db.add_item(a, "Sut")
        await db.set_bought(i1, 1)
        lists = await db.get_user_lists(1)
        self.assertEqual(len(lists), 2)
        by_name = {l["name"]: l for l in lists}
        self.assertEqual((by_name["A"]["done"], by_name["A"]["total"]), (1, 2))
        self.assertEqual((by_name["B"]["done"], by_name["B"]["total"]), (0, 0))
        # a'zo bo'lmagan foydalanuvchi ro'yxatlarni ko'rmaydi
        self.assertEqual(await db.get_user_lists(2), [])

    async def test_user_lists_sum(self):
        """Har bir ro'yxat narxlarining yig'indisi qaytadi (zaxira jadvali uchun)."""
        a = await db.create_list(1, "A")
        await db.create_list(1, "B")
        i1 = await db.add_item(a, "Non", 5000)
        await db.add_item(a, "Go'sht", 85000)
        await db.add_item(a, "Sut")  # narxsiz — yig'indiga kirmaydi
        await db.set_bought(i1, 1)
        by_name = {l["name"]: l for l in await db.get_user_lists(1)}
        self.assertEqual(by_name["A"]["sum"], 90000)
        self.assertEqual(by_name["B"]["sum"], 0)

    async def test_update_list_name(self):
        list_id = await db.create_list(1, "Eski nom")
        await db.update_list_name(list_id, "Yangi nom")
        self.assertEqual((await db.get_list(list_id))["name"], "Yangi nom")

    async def test_delete_list_cascades(self):
        list_id = await db.create_list(1, "Bozor")
        item_id = await db.add_item(list_id, "Non")
        await db.add_member(list_id, 2)
        await db.delete_list(list_id)
        self.assertIsNone(await db.get_list(list_id))
        self.assertIsNone(await db.get_item(item_id))
        self.assertEqual(await db.get_members(list_id), [])

    async def test_delete_item(self):
        list_id = await db.create_list(1, "Bozor")
        item_id = await db.add_item(list_id, "Non")
        await db.delete_item(item_id)
        self.assertEqual(await db.get_items(list_id), [])

    async def test_done_notified_flag(self):
        list_id = await db.create_list(1, "Bozor")
        self.assertEqual((await db.get_list(list_id))["done_notified"], 0)
        await db.set_done_notified(list_id, True)
        self.assertEqual((await db.get_list(list_id))["done_notified"], 1)
        await db.set_done_notified(list_id, False)
        self.assertEqual((await db.get_list(list_id))["done_notified"], 0)

    async def test_codes_unique(self):
        codes = set()
        for i in range(20):
            list_id = await db.create_list(1, f"L{i}")
            codes.add((await db.get_list(list_id))["code"])
        self.assertEqual(len(codes), 20)

    async def test_item_qty_and_updates(self):
        list_id = await db.create_list(1, "Bozor")
        item_id = await db.add_item(list_id, "Non", 5000, qty=2)
        item = await db.get_item(item_id)
        self.assertEqual(item["qty"], 2)
        await db.update_item_name(item_id, "Patir")
        await db.update_item_price(item_id, 7000)
        item = await db.get_item(item_id)
        self.assertEqual((item["name"], item["price"]), ("Patir", 7000))
        await db.update_item_price(item_id, None)
        self.assertIsNone((await db.get_item(item_id))["price"])

    async def test_last_price(self):
        list_id = await db.create_list(1, "Bozor")
        await db.add_item(list_id, "Non", 4000)
        await db.add_item(list_id, "non", 5000)  # katta-kichik harf farqsiz
        self.assertEqual(await db.last_price(1, "NON"), 5000)
        self.assertIsNone(await db.last_price(1, "Sut"))
        self.assertIsNone(await db.last_price(99, "Non"))  # begona foydalanuvchi

    async def test_duplicate_list(self):
        src = await db.create_list(1, "Haftalik")
        await db.add_member(src, 2)
        i1 = await db.add_item(src, "Non", 5000, qty=2)
        await db.set_bought(i1, 1)
        new_id = await db.duplicate_list(src, 1)
        items = await db.get_items(new_id)
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]["name"], items[0]["price"], items[0]["qty"]), ("Non", 5000, 2))
        self.assertFalse(items[0]["bought"])  # belgilar tozalanadi
        self.assertEqual(sorted(await db.get_members(new_id)), [1, 2])  # a'zolar ko'chadi

    async def test_reminder_repeat_and_manage(self):
        list_id = await db.create_list(1, "Bozor")
        rem_id = await db.add_reminder(list_id, 1, "2026-07-11 09:00")
        await db.set_reminder_repeat(rem_id, 1, "weekly")
        self.assertEqual((await db.get_reminder(rem_id))["repeat"], "weekly")
        # begona foydalanuvchi takrorni o'zgartira olmaydi
        await db.set_reminder_repeat(rem_id, 99, None)
        self.assertEqual((await db.get_reminder(rem_id))["repeat"], "weekly")
        # bump — keyingi haftaga suriladi, sent=0 qoladi
        await db.bump_reminder(rem_id, "2026-07-18 09:00")
        due = await db.due_reminders("2026-07-18 10:00")
        self.assertEqual(len(due), 1)
        # boshqarish ro'yxati va o'chirish
        mine = await db.user_reminders(1)
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]["list_name"], "Bozor")
        await db.delete_reminder(rem_id, 99)  # begona o'chira olmaydi
        self.assertEqual(len(await db.user_reminders(1)), 1)
        await db.delete_reminder(rem_id, 1)
        self.assertEqual(await db.user_reminders(1), [])

    async def test_monthly_totals(self):
        from datetime import datetime
        month = datetime.utcnow().strftime("%Y-%m")
        list_id = await db.create_list(1, "Bozor")
        i1 = await db.add_item(list_id, "Non", 5000)
        i2 = await db.add_item(list_id, "Sut", 12000)
        await db.set_bought(i1, 1)
        await db.set_bought(i2, 1)
        totals = await db.monthly_totals(1)
        self.assertEqual(totals[0], (month, 17000))

    async def test_user_names(self):
        await db.set_user_name(1, "Aziz")
        await db.set_lang(1, "ru")  # ism saqlanib qolishi kerak
        await db.set_user_name(2, "Malika")
        names = await db.get_user_names([1, 2, 3])
        self.assertEqual(names, {1: "Aziz", 2: "Malika"})

    async def test_budget(self):
        list_id = await db.create_list(1, "Bozor")
        self.assertIsNone((await db.get_list(list_id))["budget"])
        await db.set_budget(list_id, 500000)
        self.assertEqual((await db.get_list(list_id))["budget"], 500000)
        await db.set_budget(list_id, None)
        self.assertIsNone((await db.get_list(list_id))["budget"])

    async def test_remove_member(self):
        list_id = await db.create_list(1, "Bozor")
        await db.add_member(list_id, 2)
        await db.remove_member(list_id, 2)
        self.assertFalse(await db.is_member(list_id, 2))
        self.assertEqual(await db.get_members(list_id), [1])

    async def test_frequent_items(self):
        a = await db.create_list(1, "A")
        b = await db.create_list(1, "B")
        for _ in range(3):
            await db.add_item(a, "Non")
        await db.add_item(a, "Sut")
        await db.add_item(a, "Guruch")
        # b ro'yxatida "Sut" allaqachon bor — taklif qilinmasin
        await db.add_item(b, "Sut")
        suggest = await db.frequent_items(1, b)
        self.assertEqual(suggest[0], "Non")  # eng ko'p uchragan birinchi
        self.assertIn("Guruch", suggest)
        self.assertNotIn("Sut", suggest)
        # begona foydalanuvchiga takliflar chiqmaydi
        self.assertEqual(await db.frequent_items(99, b), [])

    async def test_reminders(self):
        list_id = await db.create_list(1, "Bozor")
        await db.add_reminder(list_id, 1, "2026-07-11 09:00")
        await db.add_reminder(list_id, 1, "2099-01-01 09:00")
        due = await db.due_reminders("2026-07-11 10:00")
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["list_id"], list_id)
        await db.mark_reminder_sent(due[0]["id"])
        self.assertEqual(await db.due_reminders("2026-07-11 10:00"), [])

    async def test_member_spending(self):
        list_id = await db.create_list(1, "Bozor")
        await db.add_member(list_id, 2)
        i1 = await db.add_item(list_id, "Non", 5000)
        i2 = await db.add_item(list_id, "Go'sht")
        i3 = await db.add_item(list_id, "Sut")
        await db.add_item(list_id, "Olinmagan", 999)  # olinmagan — hisobga kirmaydi
        await db.set_bought(i1, 1)          # 1-foydalanuvchi: 5000
        await db.set_bought(i2, 2, 85000)   # 2-foydalanuvchi: 85000
        await db.set_bought(i3, 1)          # 1-foydalanuvchi: narxsiz
        split = await db.member_spending(list_id)
        # eng ko'p sarflagan birinchi turadi
        self.assertEqual(split, [(2, 1, 85000), (1, 2, 5000)])

    async def test_member_spending_no_prices(self):
        """Hech narsaga narx yozilmasa ham soni bo'yicha taqsimot qaytadi."""
        list_id = await db.create_list(1, "Bozor")
        i1 = await db.add_item(list_id, "Non")
        i2 = await db.add_item(list_id, "Sut")
        await db.set_bought(i1, 1)
        await db.set_bought(i2, 1)
        self.assertEqual(await db.member_spending(list_id), [(1, 2, 0)])

    async def test_month_stats(self):
        from datetime import datetime
        month = datetime.utcnow().strftime("%Y-%m")
        list_id = await db.create_list(1, "Bozor")
        await db.add_member(list_id, 2)
        i1 = await db.add_item(list_id, "Non", 5000)
        i2 = await db.add_item(list_id, "Sut")
        await db.add_item(list_id, "Olinmagan", 999)
        await db.set_bought(i1, 1)          # men oldim — 5000
        await db.set_bought(i2, 2, 12000)   # sherik oldi — 12000
        s = await db.month_stats(1, month)
        self.assertEqual(s["items"], 2)
        self.assertEqual(s["total"], 17000)
        self.assertEqual(s["own"], 5000)
        self.assertEqual(s["lists"], 1)
        self.assertEqual(s["top"][0]["price"], 12000)


if __name__ == "__main__":
    unittest.main()
