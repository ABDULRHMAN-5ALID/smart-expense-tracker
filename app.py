import io
import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from db import (
    init_db, create_user, verify_user,
    add_expense, list_expenses, clear_all_expenses,
    update_expense, delete_expenses
)
from forecast import train_and_forecast_per_category, monthly_projection
from anomalies import detect_anomalies
from optimizer import optimize_budget
from seed_data import seed_demo

# ========== إعداد الصفحة ==========
st.set_page_config(
    page_title="متتبع المصاريف الذكي",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

SIDEBAR_WIDTH = 320

st.markdown(f"""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {{
  direction: rtl;
  text-align: right;
  font-family: "Cairo", sans-serif;
}}
[data-testid="stDataFrame"] th, [data-testid="stDataFrame"] td {{
  text-align: right !important;
  direction: rtl !important;
}}
.js-plotly-plot .plotly .main-svg {{
  direction: rtl !important;
}}
</style>
""", unsafe_allow_html=True)

# ========== تسجيل الدخول / الحساب ==========
def login_ui():
    st.title("🔐 تسجيل الدخول")

    tab1, tab2 = st.tabs(["تسجيل الدخول", "إنشاء حساب جديد"])

    with tab1:
        username = st.text_input("👤 اسم المستخدم", key="login_user")
        password = st.text_input("🔑 كلمة المرور", type="password", key="login_pass")
        if st.button("تسجيل الدخول", use_container_width=True):
            uid = verify_user(username, password)
            if uid:
                st.session_state["user_id"] = uid
                st.session_state["username"] = username
                st.success("تم تسجيل الدخول ✅")
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة ❌")

    with tab2:
        new_user = st.text_input("👤 اسم المستخدم الجديد", key="reg_user")
        new_pass = st.text_input("🔑 كلمة المرور", type="password", key="reg_pass")
        if st.button("إنشاء الحساب", use_container_width=True):
            if create_user(new_user, new_pass):
                st.success("تم إنشاء الحساب 🎉 يمكنك الآن تسجيل الدخول")
            else:
                st.error("اسم المستخدم مستخدم بالفعل ❌")

# ========== تنسيقات عامة ==========
def fmt_currency(x: float, suffix=" ريال"):
    try:
        return f"{x:,.0f}{suffix}"
    except Exception:
        return f"{x}{suffix}"

# ========== الواجهة الرئيسية ==========
def sidebar_controls(user_id: int):
    with st.sidebar:
        st.header(f"أهلاً، {st.session_state['username']} 👋")

        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.markdown("---")
        st.header("➕ إضافة مصروف جديد")
        amount = st.number_input("المبلغ", min_value=0.0, step=1.0)
        colA, colB = st.columns(2)
        with colA:
            category = st.selectbox("التصنيف", ["طعام","مواصلات","فواتير","تسوق","صحة","تعليم","ترفيه","أخرى"])
        with colB:
            payment = st.selectbox("طريقة الدفع", ["نقدًا","بطاقة","Apple Pay","STC Pay","أخرى"])
        date = st.date_input("التاريخ", value=datetime.date.today())
        note = st.text_input("ملاحظة", placeholder="وصف قصير للعملية")

        if st.button("➕ إضافة العملية", use_container_width=True):
            if amount > 0:
                add_expense(user_id, float(amount), category, payment, str(date), note)
                st.success("تمت الإضافة ✅")
                st.rerun()
            else:
                st.error("المبلغ يجب أن يكون أكبر من 0")

        if st.button("⚡ تحميل بيانات تجريبية", use_container_width=True):
            seed_demo(user_id, 100)
            st.success("تم تحميل بيانات تجريبية ✅")
            st.rerun()

        st.markdown("---")
        if st.button("🗑️ حذف جميع البيانات", use_container_width=True):
            deleted = clear_all_expenses(user_id)
            st.warning(f"تم حذف {deleted} عملية بشكل نهائي ⚠️")
            st.rerun()

# ========== التبويبات ==========
def dashboard_tab(df_all: pd.DataFrame):
    st.subheader("📊 لوحة التحكم")
    if df_all.empty:
        st.info("أضف مصروفات لرؤية اللوحة.")
        return
    df_all = df_all.copy()
    df_all["date"] = pd.to_datetime(df_all["date"])

    c1, c2, c3 = st.columns(3)
    month_mask = (df_all["date"].dt.to_period("M") == pd.Timestamp.today().to_period("M"))
    total_this_month = df_all.loc[month_mask, "amount"].sum()
    top_cat = df_all.groupby("category")["amount"].sum().sort_values(ascending=False).index[0]
    avg_per_day = df_all.groupby(df_all["date"].dt.date)["amount"].sum().mean()

    c1.metric("إجمالي هذا الشهر", fmt_currency(total_this_month))
    c2.metric("أعلى تصنيف صرف", top_cat)
    c3.metric("متوسط يومي", fmt_currency(avg_per_day))

    monthly = df_all.groupby(df_all["date"].dt.to_period("M"))["amount"].sum().reset_index()
    monthly["date"] = monthly["date"].astype(str)
    fig1 = px.bar(monthly, x="date", y="amount", title="إجمالي المصاريف الشهرية")
    st.plotly_chart(fig1, use_container_width=True)

    by_cat = df_all.groupby("category")["amount"].sum().reset_index()
    fig2 = px.pie(by_cat, values="amount", names="category", title="توزيع المصاريف حسب التصنيف")
    st.plotly_chart(fig2, use_container_width=True)
    daily = df_all.groupby(df_all["date"].dt.date)["amount"].sum().reset_index()
    daily.columns = ["date", "amount"]
    fig3 = px.line(daily, x="date", y="amount", title="المصروف اليومي")
    st.plotly_chart(fig3, use_container_width=True)


def forecast_tab(df_all: pd.DataFrame):
    st.subheader("🤖 التنبؤ بالمصروفات")
    if df_all.empty:
        st.info("لا توجد بيانات كافية للتنبؤ.")
        return
    try:
        preds_daily = train_and_forecast_per_category(df_all[["amount","category","date"]])
        preds_month = monthly_projection(preds_daily, days=30)
        pred_df = pd.DataFrame(
            [{"التصنيف": c, "توقع يومي": round(d,2), "تقدير شهري": round(preds_month[c],2)} for c, d in preds_daily.items()]
        ).sort_values("تقدير شهري", ascending=False)
        st.dataframe(pred_df, use_container_width=True)
    except Exception as e:
        st.error(f"خطأ: {e}")

def anomalies_tab(df_all: pd.DataFrame):
    st.subheader("🚨 المصاريف غير الاعتيادية")
    if df_all.empty:
        st.info("لا توجد بيانات.")
        return
    alerts = detect_anomalies(df_all[["amount","category","date"]].copy(), window_days=90, contamination=0.06)
    if alerts.empty:
        st.success("لا توجد مصاريف غير اعتيادية ✔️")
    else:
        st.dataframe(alerts, use_container_width=True)

def optimizer_tab(df_all: pd.DataFrame):
    st.subheader("🧮 مُحسّن الميزانية")
    if df_all.empty:
        st.info("أضف بيانات أولًا.")
        return
    cats = sorted(df_all["category"].unique().tolist())
    income = st.number_input("💰 الدخل الشهري", min_value=0.0, value=8000.0, step=100.0)
    target = st.number_input("🎯 هدف الادخار", min_value=0.0, value=1000.0, step=100.0)

    preds_daily = train_and_forecast_per_category(df_all[["amount","category","date"]])
    baseline = monthly_projection(preds_daily, days=30) if preds_daily else {}

    if st.button("احسب التوزيع"):
        status, allocs = optimize_budget(baseline, income, target, {}, {}, {})
        st.dataframe(pd.DataFrame([{
            "التصنيف": c,
            "المقترح": round(allocs.get(c,0.0),2)
        } for c in cats]))

def data_tab(user_id: int, df_all: pd.DataFrame):
    st.subheader("🗂️ إدارة البيانات")
    if df_all.empty:
        st.info("لا توجد بيانات.")
        return
    view_cols = ["id", "amount", "category", "payment_method", "date", "note"]
    df_view = df_all[view_cols].copy()
    edited = st.data_editor(df_view, num_rows="dynamic", use_container_width=True, disabled=["id"])

    if st.button("💾 حفظ التعديلات"):
        changed = 0
        orig = df_view.set_index("id")
        new = edited.set_index("id")
        for eid in new.index:
            diff = {}
            for col in ["amount","category","payment_method","date","note"]:
                old_val = orig.loc[eid, col]
                new_val = new.loc[eid, col]
                if old_val != new_val:
                    diff[col] = new_val
            if diff:
                changed += update_expense(user_id, int(eid), diff)
        st.success(f"تم حفظ {changed} تعديلًا ✅")
        st.rerun()

    ids = edited["id"].tolist()
    sel_to_delete = st.multiselect("اختر للحذف", ids)
    if st.button("🗑️ حذف المحدد"):
        deleted = delete_expenses(user_id, sel_to_delete)
        st.success(f"تم حذف {deleted} سجلًا ✅")
        st.rerun()

# ========== Main ==========
def main():
    init_db()
    if "user_id" not in st.session_state:
        login_ui()
        return

    user_id = st.session_state["user_id"]
    sidebar_controls(user_id)

    rows_all = list_expenses(user_id, limit=10_000)
    df_all = pd.DataFrame(rows_all)

    tabs = st.tabs(["📊 اللوحة", "🤖 التنبؤ", "🚨 غير الاعتيادية", "🧮 المُحسّن", "🗂️ البيانات"])
    with tabs[0]: dashboard_tab(df_all)
    with tabs[1]: forecast_tab(df_all)
    with tabs[2]: anomalies_tab(df_all)
    with tabs[3]: optimizer_tab(df_all)
    with tabs[4]: data_tab(user_id, df_all)

if __name__ == "__main__":
    main()
