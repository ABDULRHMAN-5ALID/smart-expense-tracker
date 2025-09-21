# anomalies.py
import pandas as pd
from sklearn.ensemble import IsolationForest

def detect_anomalies(df: pd.DataFrame, window_days: int = 90, contamination: float = 0.06) -> pd.DataFrame:
    """
    يأخذ DataFrame فيه الأعمدة: amount, category, date
    ويرجع جدول تنبيهات للشذوذ مع مستوى الشدة.
    """
    if df.empty:
        return pd.DataFrame(columns=["category", "date", "amount", "level"])

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    # نركز على آخر window_days يوم إن وُجد
    if len(data) > 0:
        max_day = data["date"].max()
        data = data[data["date"] >= (max_day - pd.Timedelta(days=window_days))]

    alerts = []
    for cat, g in data.groupby("category"):
        g = g.sort_values("date")
        if len(g) < 20:
            # بيانات قليلة: نستخدم قاعدة بسيطة
            if len(g) == 0:
                continue
            thr = g["amount"].quantile(0.95)
            out = g[g["amount"] >= thr]
            for _, r in out.iterrows():
                alerts.append({"category": cat, "date": r["date"], "amount": r["amount"], "level": "medium"})
            continue

        # نموذج IsolationForest
        X = g[["amount"]].values
        iso = IsolationForest(contamination=contamination, random_state=42)
        scores = iso.fit_predict(X)  # -1 شاذ، 1 طبيعي
        g = g.assign(is_anom=(scores == -1))

        # مستوى الشدة بالاعتماد على موقع المبلغ ضمن التوزيع
        p90 = g["amount"].quantile(0.90)
        p97 = g["amount"].quantile(0.97)
        for _, r in g[g["is_anom"]].iterrows():
            level = "high" if r["amount"] >= p97 else "medium" if r["amount"] >= p90 else "low"
            alerts.append({"category": cat, "date": r["date"], "amount": r["amount"], "level": level})

    if not alerts:
        return pd.DataFrame(columns=["category", "date", "amount", "level"])
    out_df = pd.DataFrame(alerts).sort_values(["level", "amount"], ascending=[True, False])
    return out_df
