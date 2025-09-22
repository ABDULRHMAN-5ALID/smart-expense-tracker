# optimizer.py
from typing import Dict
import pulp

def optimize_budget(
    forecast_per_cat: Dict[str, float],
    monthly_income: float,
    savings_target: float,
    fixed_bills_map: Dict[str, float] | None = None,
    min_alloc: Dict[str, float] | None = None,
    max_alloc: Dict[str, float] | None = None,
):
    """
    يحسب توزيع ميزانية مثالي للفئات بحيث:
      - مجموع المخصصات <= الدخل - هدف الادخار
      - احترام الفواتير الثابتة كحد أدنى
      - تقليل الانحراف عن baseline (التوقع/المتوسط)
    """
    fixed_bills_map = fixed_bills_map or {}
    min_alloc = min_alloc or {}
    max_alloc = max_alloc or {}

    cats = list(forecast_per_cat.keys())
    prob = pulp.LpProblem("BudgetOptimizer", pulp.LpMinimize)

    # متغيرات: alloc لكل فئة + dev+ / dev- لقياس الانحراف |alloc - baseline|
    alloc = {c: pulp.LpVariable(f"alloc_{c}", lowBound=0) for c in cats}
    dev_p = {c: pulp.LpVariable(f"devp_{c}", lowBound=0) for c in cats}
    dev_n = {c: pulp.LpVariable(f"devn_{c}", lowBound=0) for c in cats}

    # الهدف: تصغير مجموع الانحرافات
    prob += pulp.lpSum([dev_p[c] + dev_n[c] for c in cats])

    # قيود الانحراف
    for c in cats:
        prob += alloc[c] - forecast_per_cat[c] == dev_p[c] - dev_n[c]

    # قيد الدخل والادخار
    prob += pulp.lpSum([alloc[c] for c in cats]) <= monthly_income - savings_target

    for c, val in fixed_bills_map.items():
        if c in alloc:
            prob += alloc[c] >= float(val)

    for c, lo in min_alloc.items():
        if c in alloc:
            prob += alloc[c] >= float(lo)
    for c, hi in max_alloc.items():
        if c in alloc:
            prob += alloc[c] <= float(hi)

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    status = pulp.LpStatus[prob.status]
    result = {c: (alloc[c].value() if alloc[c].value() is not None else 0.0) for c in cats}
    return status, result
