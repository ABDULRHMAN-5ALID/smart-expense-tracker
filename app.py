# app.py (واجهة محسّنة RTL + تبويبات + أدوات بيانات + فلاتر شاملة)
import io
import random
import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from db import init_db, list_expenses, add_expense
from forecast import train_and_forecast_per_category, monthly_projection

st.set_page_config(page_title="متتبع المصاريف الذكي", page_icon="💸", layout="wide")

# —— تنسيقات واجهة: اتجاه عربي + تحسينات بسيطة —— #
st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
  direction: rtl; text-align: right;
}
h1, h2, h3, h4 { letter-spacing: .2px; }
.block-container { padding-top: 1.2rem; }
[data-testid="stDataFrame"] .row_heading, [data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td {
  text-align: right !important;
}
.stButton>button { border-radius: 10px; padding: .5rem 1rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ---- أدوات مساعدة ----- #
def fmt_currency(x: float, suffix=" ريال"):
    try:
        return f"{x:,.0f}{suffix}"
    except Exception:
        return f"{x}{suffix}"

def seed_demo(n=80):
    cats = ["طعام", "مواصلات", "فواتير", "تسوق", "صحة", "تعليم", "ترفيه", "أخرى"]
    pays = ["نقدًا", "بطاقة", "Apple Pay", "STC Pay", "أخرى"]
    today = datetime.date.today()
    for _ in range(n):
        days_ago = random.randint(0, 120)
        d = today - datetime.timedelta(days=days_ago)
        amount = round(random.uniform(10, 600), 2)
        add_expense(amount, random.choice(cats), random.choice(pays), str(d),
                    random.choice(["", "قهوة", "سوبرماركت", "أجرة", "فاتورة", "مطعم", "ملابس"]))

def bootstrap():
    init_db()

# ---- أقسام الواجهة ----- #
def sidebar_controls():
    with st.sidebar:
        st.header("إضافة مصروف جديد")
        amount = st.number_input("المبلغ", min_value=0.0, step=1.0)
        colA, colB = st.columns(2)
        with colA:
            category = st.selectbox("التصنيف", ["طعام","مواصلات","فواتير","تسوق","صحة","تعليم","ترفيه","أخرى"])
        with colB:
            payment = st.selectbox("طريقة الدفع", ["نقدًا","بطاقة","Apple Pay","STC Pay","أخرى"])
        date = st.date_input("التاريخ", value=datetime.date.today())
        note = st.text_input("ملاحظة", placeholder="وصف قصير للعملية")
        add_col, demo_col = st.columns([1,1])
        with add_col:
            if st.button("➕ إضافة"):
                if amount > 0:
                    add_expense(float(amount), category, payment, str(date), note)
                    st.success("تمت الإضافة ✅")
                    st.rerun()
                else:
                    st.error("المبلغ يجب أن يكون أكبر من 0")
        with demo_col:
            if st.button("⚡ تحميل بيانات تجريبية"):
                seed_demo(120)
                st.success("تم تحميل بيانات تجريبية ✅")
                st.rerun()

        st.markdown("---")
        st.subheader("استيراد/تصدير")
        # تصدير
        if st.button("⬇️ تصدير CSV"):
            rows_all = list_expenses(limit=10_000)
            df = pd.DataFrame(rows_all)
            if df.empty:
                st.info("لا توجد بيانات للتصدير.")
            else:
                buf = io.StringIO()
                df.to_csv(buf, index=False, encoding="utf-8-sig")
                st.download_button("تحميل الملف", buf.getvalue(),
                                   file_name="expenses_export.csv", mime="text/csv")
        # استيراد
        uploaded = st.file_uploader("⬆️ استيراد CSV (amount,category,payment_method,date,note)", type=["csv"])
        if uploaded is not None:
            try:
                df_up = pd.read_csv(uploaded)
                req = {"amount","category","payment_method","date"}
                if not req.issubset(set(df_up.columns)):
                    st.error("ملف CSV يجب أن يحتوي الأعمدة: amount, category, payment_method, date (و note اختياري).")
                else:
                    for _, r in df_up.iterrows():
                        add_expense(float(r["amount"]), str(r["category"]),
                                    str(r["payment_method"]), str(r["date"]), str(r.get("note","") or ""))
                    st.success(f"تم استيراد {len(df_up)} عملية ✅")
                    st.rerun()
            except Exception as e:
                st.error(f"تعذّر الاستيراد: {e}")

def dashboard_tab(df_all: pd.DataFrame):
    st.subheader("📊 لوحة التحكم")
    if df_all.empty:
        st.info("أضف مصروفات لرؤية اللوحة.")
        return

    df_all = df_all.copy()
    df_all["date"] = pd.to_datetime(df_all["date"])

    # KPIs
    c1, c2, c3 = st.columns(3)
    month_mask = (df_all["date"].dt.to_period("M") == pd.Timestamp.today().to_period("M"))
    total_this_month = df_all.loc[month_mask, "amount"].sum()
    top_cat = df_all.groupby("category")["amount"].sum().sort_values(ascending=False).index[0]
    avg_per_day = df_all.groupby(df_all["date"].dt.date)["amount"].sum().mean()

    c1.metric("إجمالي هذا الشهر", fmt_currency(total_this_month))
    c2.metric("أعلى تصنيف صرف", top_cat)
    c3.metric("متوسط يومي", fmt_currency(avg_per_day))

    # الرسوم
    monthly = df_all.groupby(df_all["date"].dt.to_period("M"))["amount"].sum().reset_index()
    monthly["date"] = monthly["date"].astype(str)
    fig1 = px.bar(monthly, x="date", y="amount", title="إجمالي المصاريف الشهرية")
    st.plotly_chart(fig1, use_container_width=True)

    by_cat = df_all.groupby("category")["amount"].sum().reset_index()
    fig2 = px.pie(by_cat, values="amount", names="category", title="توزيع المصاريف حسب التصنيف")
    st.plotly_chart(fig2, use_container_width=True)

    daily = df_all.groupby(df_all["date"].dt.date)["amount"].sum().reset_index()
    fig3 = px.line(daily, x="date", y="amount", title="المصروف اليومي")
    st.plotly_chart(fig3, use_container_width=True)

def forecast_tab(df_all: pd.DataFrame):
    st.subheader("🤖 التنبؤ بالمصروفات")
    if df_all.empty:
        st.info("لا توجد بيانات كافية للتنبؤ.")
        return
    try:
        df_small = df_all[["amount","category","date"]].copy()
        preds_daily = train_and_forecast_per_category(df_small)
        if not preds_daily:
            st.info("أضف مصروفات أكثر لإظهار التوقعات.")
            return
        preds_month = monthly_projection(preds_daily, days=30)
        pred_df = pd.DataFrame(
            [{"التصنيف": c, "توقع يومي": round(d,2), "تقدير شهري": round(preds_month[c],2)} for c, d in preds_daily.items()]
        ).sort_values("تقدير شهري", ascending=False)
        st.dataframe(pred_df, use_container_width=True)
        st.caption("ملاحظة: مع قلة البيانات يُستخدم متوسط بسيط.")
    except Exception as e:
        st.error(f"خطأ في التنبؤ: {e}")

def anomalies_tab(df_all: pd.DataFrame):
    st.subheader("🚨 المصاريف غير الاعتيادية (آخر ٩٠ يومًا)")
    if df_all.empty:
        st.info("لا توجد بيانات كافية.")
        return
    try:
        from anomalies import detect_anomalies
        alerts = detect_anomalies(df_all[["amount","category","date"]].copy(), window_days=90, contamination=0.06)
        if alerts.empty:
            st.success("لا توجد مصاريف غير اعتيادية حاليًا ✔️")
            return
        alerts = alerts.sort_values(["level","date"], ascending=[True, False])
        level_map = {"high": "عالية","medium":"متوسطة","low":"منخفضة"}
        alerts["المستوى"] = alerts["level"].map(level_map)
        alerts["التاريخ"] = pd.to_datetime(alerts["date"]).dt.date
        alerts = alerts.rename(columns={"category":"التصنيف","amount":"المبلغ"})
        alerts = alerts[["التصنيف","التاريخ","المبلغ","المستوى"]]
        st.dataframe(alerts, use_container_width=True)
        st.caption("يتم التقدير بنموذج IsolationForest وحدود مئوية لكل تصنيف.")
    except Exception as e:
        st.error(f"خطأ في الكشف عن الشذوذ: {e}")

def optimizer_tab(df_all: pd.DataFrame):
    st.subheader("🧮 مُحسّن الميزانية")
    if df_all.empty:
        st.info("أضف بيانات أولًا.")
        return

    df = df_all.copy()
    df["date"] = pd.to_datetime(df["date"])
    cats = sorted(df["category"].unique().tolist())

    col1, col2 = st.columns(2)
    with col1:
        income = st.number_input("الدخل الشهري", min_value=0.0, value=8000.0, step=100.0)
    with col2:
        target = st.number_input("هدف الادخار", min_value=0.0, value=1000.0, step=100.0)

    st.markdown("**حدود اختيارية:**")
    fixed_map, min_bounds, max_bounds = {}, {}, {}
    with st.expander("تحديد حدود/فواتير لكل فئة (اختياري)"):
        for c in cats:
            c1,c2,c3 = st.columns(3)
            with c1:
                fixed_map[c] = st.number_input(f"حد أدنى ثابت لـ «{c}»", min_value=0.0, value=0.0, step=50.0, key=f"fix_{c}")
            with c2:
                min_bounds[c] = st.number_input(f"حد أدنى لـ «{c}»", min_value=0.0, value=0.0, step=50.0, key=f"min_{c}")
            with c3:
                max_bounds[c] = st.number_input(f"حد أقصى لـ «{c}»", min_value=0.0, value=0.0, step=50.0, key=f"max_{c}")

    # baseline
    try:
        preds_daily = train_and_forecast_per_category(df[["amount","category","date"]])
        baseline = monthly_projection(preds_daily, days=30) if preds_daily else {}
    except Exception:
        baseline = {}
    if not baseline:
        g = df.groupby([df["date"].dt.to_period("M"), "category"])["amount"].sum().reset_index()
        month_cat = g.groupby("category")["amount"].mean().to_dict()
        baseline = {c: float(month_cat.get(c, 0.0)) for c in cats}

    st.markdown("**الأساس (Baseline) من التنبؤ/المتوسط:**")
    st.dataframe(pd.DataFrame([{"التصنيف": c, "الأساس (ريال)": round(baseline.get(c,0.0),2)} for c in cats]),
                 use_container_width=True)

    if st.button("احسب التوزيع المقترح"):
        try:
            from optimizer import optimize_budget
            status, allocs = optimize_budget(
                forecast_per_cat=baseline,
                monthly_income=income,
                savings_target=target,
                fixed_bills_map=fixed_map,
                min_alloc=min_bounds,
                max_alloc={k:v for k,v in max_bounds.items() if v>0}
            )
            if status != "Optimal":
                st.warning(f"الحل ليس مثاليًا ({status}). جرّب تعديل الحدود أو تقليل هدف الادخار.")
            compare = pd.DataFrame([{
                "التصنيف": c,
                "الأساس (ريال)": round(baseline.get(c,0.0),2),
                "المقترح (ريال)": round(allocs.get(c,0.0),2),
                "الفرق": round(allocs.get(c,0.0)-baseline.get(c,0.0),2)
            } for c in cats]).sort_values("المقترح (ريال)", ascending=False)
            st.success("تم الحساب ✅")
            st.dataframe(compare, use_container_width=True)
            total_alloc = sum(allocs.values())
            st.caption(f"إجمالي المخصصات: {fmt_currency(total_alloc)} — المتاح بعد الادخار: {fmt_currency(income - target)}")
        except Exception as e:
            st.error(f"خطأ أثناء التحسين: {e}")

def data_tab(df_all: pd.DataFrame):
    st.subheader("🗂️ إدارة البيانات (تحرير + حذف)")

    if df_all.empty:
        st.info("لا توجد بيانات بعد.")
        return

    # نعرض الأعمدة القابلة للتحرير
    view_cols = ["id", "amount", "category", "payment_method", "date", "note"]
    df_view = df_all[view_cols].copy()

    st.caption("انقر مرتين على الخلية لتعديلها. لا يمكن تعديل العمود (id).")
    edited = st.data_editor(
        df_view,
        num_rows="dynamic",
        use_container_width=True,
        disabled=["id"],  # id ثابت
        column_config={
            "amount": st.column_config.NumberColumn("amount", step=1.0, help="المبلغ"),
            "category": st.column_config.SelectboxColumn("category", options=["طعام","مواصلات","فواتير","تسوق","صحة","تعليم","ترفيه","أخرى"]),
            "payment_method": st.column_config.SelectboxColumn("payment_method", options=["نقدًا","بطاقة","Apple Pay","STC Pay","أخرى"]),
            "date": st.column_config.DateColumn("date"),
            "note": st.column_config.TextColumn("note"),
        },
        key="editor_table",
    )

    # ——— حفظ التعديلات ———
    save_col, del_col = st.columns([1,1])
    with save_col:
        if st.button("💾 حفظ التعديلات"):
            try:
                # قارن الصفوف: أي صف تغيّر نحدّثه
                from db import update_expense
                changed = 0
                orig = df_view.set_index("id")
                new = edited.set_index("id")
                for eid in new.index:
                    diff = {}
                    for col in ["amount","category","payment_method","date","note"]:
                        old_val = None if eid not in orig.index else orig.loc[eid, col]
                        new_val = new.loc[eid, col]
                        # توحيد التاريخ إلى نص ISO
                        if col == "date" and pd.notna(new_val):
                            new_val = pd.to_datetime(new_val).date().isoformat()
                            old_val = pd.to_datetime(old_val).date().isoformat() if pd.notna(old_val) else old_val
                        if (pd.isna(old_val) and pd.notna(new_val)) or (pd.notna(old_val) and pd.isna(new_val)) or (old_val != new_val):
                            diff[col] = new_val
                    if diff:
                        changed += update_expense(int(eid), diff)
                st.success(f"تم حفظ {changed} تعديلًا ✅")
                st.rerun()
            except Exception as e:
                st.error(f"تعذّر الحفظ: {e}")

    # ——— الحذف ———
    with del_col:
        # واجهة اختيار صفوف للحذف
        ids = edited["id"].tolist()
        sel_to_delete = st.multiselect("اختر السجلات المراد حذفها", ids, label_visibility="collapsed")
        if st.button("🗑️ حذف المحدد"):
            try:
                from db import delete_expenses
                deleted = delete_expenses([int(i) for i in sel_to_delete])
                st.success(f"تم حذف {deleted} سجلًا ✅")
                st.rerun()
            except Exception as e:
                st.error(f"تعذّر الحذف: {e}")

# —— دالة الفلاتر ——
def apply_filters(df: pd.DataFrame,
                  date_range,
                  cats,
                  pays,
                  amount_min,
                  amount_max) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.date
    if date_range:
        start, end = date_range
        out = out[(out["date"] >= start) & (out["date"] <= end)]
    if cats:
        out = out[out["category"].isin(cats)]
    if pays:
        out = out[out["payment_method"].isin(pays)]
    if amount_min is not None:
        out = out[out["amount"] >= amount_min]
    if amount_max is not None and amount_max > 0:
        out = out[out["amount"] <= amount_max]
    return out

def main():
    bootstrap()
    st.title("💸 متتبع المصاريف الذكي — واجهة محسّنة")

    # عناصر الشريط الجانبي (إضافة + أدوات بيانات)
    sidebar_controls()

    # تحميل البيانات
    rows_all = list_expenses(limit=10_000)
    df_all = pd.DataFrame(rows_all)

    # ——— شريط فلاتر تفاعلي ———
    st.markdown("### 🎛️ الفلاتر")
    if df_all.empty:
        st.info("لا توجد بيانات بعد لاستخدام الفلاتر.")
        filt_df = df_all
    else:
        df_all["date"] = pd.to_datetime(df_all["date"])
        min_d = df_all["date"].min().date()
        max_d = df_all["date"].max().date()
        colF1, colF2, colF3 = st.columns([2,2,2])

        with colF1:
            dr = st.date_input("الفترة", value=(min_d, max_d))
            if isinstance(dr, tuple) and len(dr) == 2:
                date_range = (dr[0], dr[1])
            else:
                date_range = (min_d, max_d)

        cats_all = sorted(df_all["category"].unique().tolist())
        pays_all = sorted(df_all["payment_method"].unique().tolist())

        with colF2:
            cats_sel = st.multiselect("التصنيفات", cats_all, default=cats_all)

        with colF3:
            pays_sel = st.multiselect("طرق الدفع", pays_all, default=pays_all)

        cMin, cMax = st.columns(2)
        with cMin:
            a_min = st.number_input("الحد الأدنى للمبلغ", min_value=0.0, value=0.0, step=10.0)
        with cMax:
            a_max = st.number_input("الحد الأقصى للمبلغ (اختياري)", min_value=0.0, value=0.0, step=10.0)

        # تطبيق الفلاتر
        filt_df = apply_filters(
            df_all,
            date_range=date_range,
            cats=cats_sel,
            pays=pays_sel,
            amount_min=a_min,
            amount_max=a_max if a_max > 0 else None
        )

        st.caption(f"النتائج بعد الفلترة: {len(filt_df)} عملية من أصل {len(df_all)}.")

    # —— تبويبات مرتبطة بالفلاتر —— #
    tabs = st.tabs(["📊 اللوحة", "🤖 التنبؤ", "🚨 غير الاعتيادية", "🧮 المُحسّن", "🗂️ البيانات"])
    with tabs[0]: dashboard_tab(filt_df)
    with tabs[1]: forecast_tab(filt_df)
    with tabs[2]: anomalies_tab(filt_df)
    with tabs[3]: optimizer_tab(filt_df)
    with tabs[4]: data_tab(filt_df)

if __name__ == "__main__":
    main()
