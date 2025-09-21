# seed_data.py
import random
import datetime
from db import add_expense, init_db

categories = ["طعام", "مواصلات", "فواتير", "تسوق", "صحة", "تعليم", "ترفيه", "أخرى"]
payments = ["نقدًا", "بطاقة", "Apple Pay", "STC Pay", "أخرى"]

def seed(n=50):
    init_db()
    today = datetime.date.today()
    for _ in range(n):
        days_ago = random.randint(0, 120)  # خلال آخر 4 شهور
        date = today - datetime.timedelta(days=days_ago)
        amount = round(random.uniform(10, 600), 2)
        category = random.choice(categories)
        payment = random.choice(payments)
        note = random.choice(["", "قهوة", "سوبرماركت", "أجرة", "فاتورة", "مطعم", "ملابس"])
        add_expense(amount, category, payment, str(date), note)
    print(f"✅ تمت إضافة {n} عملية عشوائية.")

if __name__ == "__main__":
    seed(100)  # عدّل الرقم لو تبغى أكثر/أقل
