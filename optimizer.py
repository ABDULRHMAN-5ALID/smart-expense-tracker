import pulp
import pandas as pd
from db import list_expenses

def optimize_budget(income: float, saving_goal: float, user_id: int, month: int = None, year: int = None):
    """
    مُحسّن الميزانية الذكي مع حدود دنيا وعليا لكل تصنيف.
    """
    available = income - saving_goal
    if available <= 0:
        return {}

    rows = list_expenses(limit=1000, month=month, year=year, user_id=user_id)
    df = pd.DataFrame(rows)

    # التصنيفات الأساسية
    categories = ["طعام", "مواصلات", "ترفيه", "تسوق", "تعليم", "صحة", "فواتير", "أخرى"]

    # لو ما فيه بيانات، وزع بالتساوي
    if df.empty:
        share = available / len(categories)
        return {cat: round(share, 2) for cat in categories}

    # حساب النسب من البيانات السابقة
    category_totals = df.groupby("category")["amount"].sum()
    total_spent = category_totals.sum()
    proportions = {cat: (category_totals[cat] / total_spent) if cat in category_totals else 1/len(categories) for cat in categories}

    # إنشاء نموذج LP
    prob = pulp.LpProblem("BudgetOptimizer", pulp.LpMaximize)

    # متغيرات التوزيع
    alloc = {cat: pulp.LpVariable(cat, lowBound=0) for cat in categories}

    # دالة الهدف = تعظيم التوزيع حسب العادات السابقة
    prob += pulp.lpSum([alloc[cat] * proportions[cat] for cat in categories])

    # مجموع التوزيع = المتاح
    prob += pulp.lpSum([alloc[cat] for cat in categories]) == available

    # حد أدنى (5%) وحد أقصى (30%)
    for cat in categories:
        prob += alloc[cat] >= 0.05 * available
        prob += alloc[cat] <= 0.30 * available

    # حل المسألة
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    return {cat: round(alloc[cat].value(), 2) for cat in categories}
