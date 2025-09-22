# forecast.py
import pandas as pd
import numpy as np
from dateutil import parser

try:
    import xgboost as xgb
    HAS_XGB = True
except Exception:
    HAS_XGB = False

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['month'] = df['date'].dt.month
    df['dow'] = df['date'].dt.dayofweek
    df['is_weekend'] = (df['dow'] >= 5).astype(int)

    parts = []
    for cat, g in df.groupby('category'):
        g = g.sort_values('date').copy()
        g['lag7']  = g['amount'].shift(7)
        g['lag14'] = g['amount'].shift(14)
        g['lag28'] = g['amount'].shift(28)
        g['roll7'] = g['amount'].rolling(7, min_periods=1).mean()
        parts.append(g)
    out = pd.concat(parts).fillna(0.0)
    return out

def train_and_forecast_per_category(df: pd.DataFrame) -> dict:

    if df.empty:
        return {}

    df = build_features(df)
    preds = {}

    for cat, g in df.groupby('category'):
        X = g[['month','dow','is_weekend','lag7','lag14','lag28','roll7']]
        y = g['amount']

        # بيانات قليلة → متوسط
        if len(g) < 40 or not HAS_XGB:
            preds[cat] = float(y.tail(14).mean() if len(y) >= 14 else y.mean() if len(y) else 0.0)
            continue

        model = xgb.XGBRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.07,
            subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0,
            objective="reg:squarederror", random_state=42
        )
        model.fit(X, y)
        x_last = X.tail(1).values
        preds[cat] = float(model.predict(x_last)[0])

    return preds

def monthly_projection(preds_daily: dict, days=30) -> dict:
    return {k: float(v) * days for k, v in preds_daily.items()}
