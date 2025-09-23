# seed_data.py
import random
import datetime
from db import add_expense

def seed_demo(user_id: int, n: int = 120):
    cats = ["طعام", "مواصلات", "فواتير", "تسوق", "صحة", "تعليم", "ترفيه", "أخرى"]
    pays = ["نقدًا", "بطاقة", "Apple Pay", "STC Pay", "أخرى"]
    today = datetime.date.today()
    for _ in range(n):
        days_ago = random.randint(0, 120)
        d = today - datetime.timedelta(days=days_ago)
        amount = round(random.uniform(10, 600), 2)
        add_expense(
            user_id,
            amount,
            random.choice(cats),
            random.choice(pays),
            str(d),
            random.choice(["", "قهوة", "سوبرماركت", "أجرة", "فاتورة", "مطعم", "ملابس"]),
        )
