import streamlit as st
import sqlite3
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


# --- Page Config: Wide layout for dashboard ---
st.set_page_config(layout="wide", page_title="Group 4 - Revenue & Growth")

# --- CSS: Readable headline and KPI cards ---
st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 13px !important; }
    h1 { font-size: 22px !important; }
    .headline {
        background: #E0E7FF;
        border-left: 4px solid #4F46E5;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 12px;
        color: #1E1B4B !important;
        line-height: 1.4;
        margin-bottom: 10px;
    }
    .scope {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 12px;
        color: #334155;
        margin-bottom: 12px;
    }
    /* Fix for columns gap so borders don't enter each other */
    div[data-testid="column"] {
        padding: 8px !important;
    }
    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 16px 0 14px 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #E2E8F0;
        text-align: center;
        min-height: 140px;
    }
    .kpi-header { 
        height: 8px; 
        border-radius: 14px 14px 0 0;
        margin-top: -16px;
        margin-bottom: 12px;
    }
    .kpi-icon {
        width: 48px; height: 48px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 8px auto;
        font-size: 22px;
        color: white;
    }
    .kpi-title { font-size: 12px; font-weight: 600; margin-bottom: 4px; }
    .kpi-value { font-size: 20px; font-weight: 900; color: #0F172A; }
</style>
""", unsafe_allow_html=True)

# --- Color Palette: Indigo, Green, Orange, Red, Purple ---
COLORS = ["#4F46E5", "#059669", "#D97706", "#DC2626", "#7C3AED"]
sns.set_style("whitegrid")
plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11}) # Small readable fonts for charts

# --- DB Connection: Use in-memory SQLite to avoid empty olist.db file issue ---

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    # For Streamlit Cloud - use relative path, not C:\...
    files = {
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "order_payments": "olist_order_payments_dataset.csv",
        "customers": "olist_customers_dataset.csv"
    }
    for table, path in files.items():
        pd.read_csv(path).to_sql(table, conn, if_exists="replace", index=False)
    return conn

conn = get_conn()

# --- Cached Query Runner: One decorator for all queries ---
@st.cache_data
def run_query(sql, params):
    """Run SQL with params, return DataFrame. Cached for performance."""
    return pd.read_sql_query(sql, conn, params=params)

# --- Helper Functions for Filters: Handle placeholder counts correctly ---
def year_multi(y, m): 
    """Need 4 placeholders: 2 for year, 2 for state JSON"""
    return (y, y, m, m)

def multi_params(m): 
    """Need 2 placeholders: for state only queries (YoY)"""
    return (m, m)

def get_states_list():
    """Get distinct list of customer states for filter dropdown"""
    return pd.read_sql_query("SELECT DISTINCT customer_state FROM customers WHERE customer_state IS NOT NULL ORDER BY customer_state", conn)["customer_state"].tolist()

def normalize_state_json(lst):
    """Convert selected states to JSON array. Empty [] means All states."""
    if not lst or "All" in lst:
        return json.dumps([])
    return json.dumps([s for s in lst if s != "All"])

def fmt_smart(v):
    """Smart formatting: <1M shows as R$ 520K, >=1M as R$ 1.18M with 2 decimals"""
    if pd.isna(v): return "R$ 0"
    if v >= 1_000_000: return f"R$ {v/1e6:.2f}M"
    else: return f"R$ {v/1000:.0f}K"

# ---- CHARTS ----
def monthly_chart(df):
    """Chart 1: Monthly GMV Trend - Peak Month annotation with red arrow"""
    fig, ax = plt.subplots(figsize=(10, 4))
    if df.empty:
        return fig
    ax.plot(df["month"], df["gmv"], marker="o", color=COLORS[0], linewidth=2.2, markersize=5)
    # Annotate peak month (2017-11) with red arrow
    peak = df.loc[df["gmv"].idxmax()]
    ax.annotate(f'PEAK {peak["month"]}\n{fmt_smart(peak["gmv"])}',
                xy=(peak["month"], peak["gmv"]), xytext=(0, 35),
                textcoords="offset points", fontsize=9, color="#DC2626", weight="bold", ha="center",
                arrowprops=dict(arrowstyle="->", color="#DC2626", lw=1.2))
    ax.set_title("Monthly GMV Trend - Peak Nov 2017 Black Friday", loc="left", fontsize=12, weight="bold", pad=12)
    ax.set_xlabel("Order Purchase Month (YYYY-MM)", fontsize=10, weight="bold") # X label explicit
    ax.set_ylabel("Total GMV per Month (R$)", fontsize=10, weight="bold") # Y label explicit
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig

def state_chart(df):
    """Chart 2: Top 10 Revenue by State - Horizontal bar chart"""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if df.empty:
        return fig
    df = df.sort_values("gmv", ascending=True) # Sort for horizontal bar readability
    ax.barh(df["state"], df["gmv"], color=COLORS[0], height=0.55, edgecolor="white")
    # Bar labels with increased font (+2) as requested: from 8 to 10
    for i, (gmv, orders) in enumerate(zip(df["gmv"], df["orders"])):
        ax.text(gmv*1.01, i, f"{fmt_smart(gmv)} (n={orders:,})", va="center", fontsize=10, weight="bold")
    ax.set_title("Revenue by State - Top 10", loc="left", fontsize=12, weight="bold")
    ax.set_xlabel("Total GMV per State (R$)", fontsize=10, weight="bold")
    ax.set_ylabel("Customer State", fontsize=10, weight="bold")
    plt.tight_layout()
    return fig

def payment_chart(df):
    """Chart 3: Payment Type Breakdown - Pie chart with %"""
    fig, ax = plt.subplots(figsize=(6, 4))
    if df.empty:
        return fig
    total = df["transactions"].sum()
    labels = [f"{row['payment_type']} ({row['transactions']/total*100:.1f}%)" for _, row in df.iterrows()]
    wedges, _ = ax.pie(df["transactions"], colors=COLORS, startangle=90, wedgeprops={'edgecolor':'white','linewidth':1.5})
    ax.legend(wedges, labels, title="Payment Type", loc="center left", bbox_to_anchor=(1,0,0.5,1), frameon=False, fontsize=9)
    ax.set_title("Payment Type Breakdown", loc="left", fontsize=12, weight="bold")
    plt.tight_layout()
    return fig

def yoy_chart(df):
    """Chart 4: YoY GMV Comparison - Bar chart"""
    fig, ax = plt.subplots(figsize=(7, 3.8))
    if df.empty:
        return fig
    bars = ax.bar(df["year"], df["gmv"], color=COLORS[:len(df)], width=0.6, edgecolor="white")
    for bar, row in zip(bars, df.itertuples()):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.03, f"{fmt_smart(row.gmv)}\n(n={row.orders:,})", ha="center", fontsize=9, weight="bold")
    ax.set_title("Year-over-Year GMV Comparison", loc="left", fontsize=12, weight="bold")
    ax.set_xlabel("Year", fontsize=10, weight="bold")
    ax.set_ylabel("Total GMV per Year (R$)", fontsize=10, weight="bold")
    plt.tight_layout()
    return fig

def instalment_chart(df):
    """Chart 5 (Advanced): Payment Instalments 0-24"""
    fig, ax = plt.subplots(figsize=(9, 3.8))
    if df.empty:
        return fig
    bars = ax.bar(df["instalments"], df["transactions"], color=COLORS[0], width=0.7, edgecolor="white")
    for bar, row in zip(bars, df.itertuples()):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.02, f"{row.transactions:,}", ha="center", fontsize=8, weight="bold")
    ax.set_title("Payment Instalments Distribution (0-24)", loc="left", fontsize=12, weight="bold")
    ax.set_xlabel("Number of Payment Instalments (parcelas)", fontsize=10, weight="bold")
    ax.set_ylabel("Number of Transactions", fontsize=10, weight="bold")
    plt.tight_layout()
    return fig

# --- QUERIES: All use JOIN customers + state filter guard (?='[]' OR state IN json_each) ---
def q1_kpis(y,s):
    """KPI Query: Verified Total GMV R$15,843,553.24 = SUM(price+freight), no status filter"""
    sql = """WITH m AS (SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month, SUM(i.price+i.freight_value) AS gmv FROM order_items i JOIN orders o ON i.order_id=o.order_id JOIN customers c ON o.customer_id=c.customer_id WHERE (?='All' OR strftime('%Y', o.order_purchase_timestamp)=?) AND (?='[]' OR c.customer_state IN (SELECT value FROM json_each(?))) GROUP BY month),
    p AS (SELECT op.payment_value, op.payment_type FROM order_payments op JOIN orders o ON op.order_id=o.order_id JOIN customers c ON o.customer_id=c.customer_id WHERE (?='All' OR strftime('%Y', o.order_purchase_timestamp)=?) AND (?='[]' OR c.customer_state IN (SELECT value FROM json_each(?))))
    SELECT ROUND(SUM(gmv),2) AS total_gmv, (SELECT month FROM m ORDER BY gmv DESC LIMIT 1) AS peak_month, (SELECT ROUND(gmv,2) FROM m ORDER BY gmv DESC LIMIT 1) AS peak_month_gmv, (SELECT ROUND(AVG(payment_value),2) FROM p) AS avg_payment_value, (SELECT ROUND(100.0*SUM(CASE WHEN payment_type='credit_card' THEN 1 ELSE 0 END)/COUNT(*),1) FROM p) AS credit_card_pct FROM m"""
    return run_query(sql, (y,y,s,s, y,y,s,s))

def q2_monthly(y,s):
    """Monthly Trend: GROUP BY YYYY-MM for Monthly GMV"""
    return run_query("""SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month, ROUND(SUM(i.price+i.freight_value),2) AS gmv FROM orders o JOIN order_items i ON o.order_id=i.order_id JOIN customers c ON o.customer_id=c.customer_id WHERE (?='All' OR strftime('%Y', o.order_purchase_timestamp)=?) AND (?='[]' OR c.customer_state IN (SELECT value FROM json_each(?))) GROUP BY month ORDER BY month""", year_multi(y,s))

def q3_state(y,s):
    """State Revenue: Top 10 states by GMV, COUNT(DISTINCT order_id) to avoid fan-out"""
    return run_query("""SELECT c.customer_state AS state, ROUND(SUM(i.price+i.freight_value),2) AS gmv, COUNT(DISTINCT i.order_id) AS orders FROM order_items i JOIN orders o ON i.order_id=o.order_id JOIN customers c ON o.customer_id=c.customer_id WHERE (?='All' OR strftime('%Y', o.order_purchase_timestamp)=?) AND (?='[]' OR c.customer_state IN (SELECT value FROM json_each(?))) GROUP BY state ORDER BY gmv DESC LIMIT 10""", year_multi(y,s))

def q4_payment(y,s):
    """Payment Type: Must JOIN customers for state filter (bug fix from Claude review)"""
    return run_query("""SELECT op.payment_type, COUNT(*) AS transactions FROM order_payments op JOIN orders o ON op.order_id=o.order_id JOIN customers c ON o.customer_id=c.customer_id WHERE (?='All' OR strftime('%Y', o.order_purchase_timestamp)=?) AND (?='[]' OR c.customer_state IN (SELECT value FROM json_each(?))) GROUP BY payment_type ORDER BY transactions DESC""", year_multi(y,s))

def q5_yoy(s):
    """YoY: Yearly GMV, note 2016 Sep,Oct,Dec only, 2018 ends Oct 17"""
    return run_query("""SELECT strftime('%Y', o.order_purchase_timestamp) AS year, ROUND(SUM(i.price+i.freight_value),2) AS gmv, COUNT(DISTINCT o.order_id) AS orders FROM order_items i JOIN orders o ON i.order_id=o.order_id JOIN customers c ON o.customer_id=c.customer_id WHERE (?='[]' OR c.customer_state IN (SELECT value FROM json_each(?))) GROUP BY year ORDER BY year""", multi_params(s))

def q6_instalments(y,s):
    """Instalments: CAST to INT for 0-24 sorting, only credit_card payment_type"""
    return run_query("""SELECT CAST(op.payment_installments AS INTEGER) AS instalments, COUNT(*) AS transactions FROM order_payments op JOIN orders o ON op.order_id=o.order_id JOIN customers c ON o.customer_id=c.customer_id WHERE op.payment_type='credit_card' AND (?='All' OR strftime('%Y', o.order_purchase_timestamp)=?) AND (?='[]' OR c.customer_state IN (SELECT value FROM json_each(?))) GROUP BY instalments ORDER BY instalments""", year_multi(y,s))

# ---- MAIN DASHBOARD ----
st.title("📈 Revenue & Growth Dashboard")
st.markdown("**Group 4 Capstone Project | Brazilian Olist E-commerce**")

# --- Sidebar ---
st.sidebar.title("🎛️ Filters")
st.sidebar.markdown("Filter all charts by Year and by State")
st.sidebar.markdown("---")
states_list = get_states_list()
selected_year = st.sidebar.selectbox("📅 Filter by Year", ["All","2016","2017","2018"])
selected_state_raw = st.sidebar.multiselect("🗺️ Filter by Customer State", ["All"] + states_list, default=["All"])
state_json = normalize_state_json(selected_state_raw)
st.sidebar.markdown("---")
st.sidebar.caption(f"Filtering: {selected_year} | {', '.join(selected_state_raw) if len(selected_state_raw) <=3 else f'{len(selected_state_raw)} states'}")

# --- Tabs: Overview / Revenue & Growth / Detail & Method ---
tab_overview, tab_theme, tab_detail = st.tabs(["Overview", "Revenue & Growth", "Detail & Method"])

with tab_overview:
    st.markdown("""
    <div class="scope">
    <b>Scope:</b> As Revenue & Growth, we analyzed Total GMV (price + freight_value), Monthly GMV Trend, Revenue by State, Payment Type, and Payment Instalments. 
    We use the year filter and state filter to see how GMV changes over time, where revenue concentrates, and how payment type and payment instalments drive sales.
    </div>
    """, unsafe_allow_html=True)
    
    kpi_df = q1_kpis(selected_year, state_json)
    if kpi_df.empty or pd.isna(kpi_df.iloc[0]["total_gmv"]):
        st.info("No data for this filter selection")
    else:
        k = kpi_df.iloc[0]
        df2 = q2_monthly(selected_year, state_json)
        if not df2.empty:
            # Insight from graph, SP 37.38% of GMV
            headline = f"""Our Monthly GMV Trend shows low sales in late 2016, steady growth through 2017, and a sharp peak in <b>{k['peak_month']} at {fmt_smart(k['peak_month_gmv'])}</b> during Black Friday. 
            Total GMV is {fmt_smart(k['total_gmv'])} with Average Payment Value of R$ {k['avg_payment_value']} and Credit Card Payment Type at {k['credit_card_pct']}%. 
            When we filter by All states, SP state alone is 37.38% of Total GMV (R$5.92M) — showing high state concentration."""
        else:
            headline = f"Peak month is {k['peak_month']} at {fmt_smart(k['peak_month_gmv'])}."
        
        # Insight
        st.markdown(f'<div class="headline"><b>Insight:</b> {headline}</div>', unsafe_allow_html=True)
        
        # KPI Cards
        c1,c2,c3,c4,c5 = st.columns(5)
        kpis = [
            {"title": "Total GMV", "value": fmt_smart(k['total_gmv']), "color": "#4F46E5", "icon": "📈"},
            {"title": "Peak Month", "value": k['peak_month'], "color": "#059669", "icon": "📅"},
            {"title": "Peak GMV", "value": fmt_smart(k['peak_month_gmv']), "color": "#D97706", "icon": "🔥"},
            {"title": "Avg Payment", "value": f"R$ {k['avg_payment_value']:,.2f}", "color": "#DC2626", "icon": "💲"},
            {"title": "Credit Card", "value": f"{k['credit_card_pct']}%", "color": "#7C3AED", "icon": "💳"},
        ]
        for col, kpi in zip([c1,c2,c3,c4,c5], kpis):
            col.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-header" style="background:{kpi['color']};"></div>
                <div class="kpi-icon" style="background:{kpi['color']};">{kpi['icon']}</div>
                <div class="kpi-title" style="color:{kpi['color']};">{kpi['title']}</div>
                <div class="kpi-value">{kpi['value']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.write("")
        st.pyplot(monthly_chart(df2))

with tab_theme:
    # Insight
    st.markdown("""
    <div class="headline">
    <b>Insight:</b> Revenue by State shows SP contributes 37.38% of Total GMV (R$5.92M), with RJ and MG far behind — high concentration risk. 
    Payment Type shows Credit Card Payment Type dominates at 73.9% of transactions. 
    Year-over-Year GMV Comparison shows 2016 is incomplete (only Sep, Oct, Dec), 2017 is our only full year, and 2018 stops in October — so 2017 naturally shows highest Yearly GMV. The common pattern across 2016, 2017, 2018 is Q4 always brings more GMV than other quarters.
    </div>
    """, unsafe_allow_html=True)
    
    colA, colB = st.columns(2)
    with colA: 
        df3 = q3_state(selected_year, state_json)
        st.pyplot(state_chart(df3))
    with colB:
        df4 = q4_payment(selected_year, state_json)
        st.pyplot(payment_chart(df4))
        st.dataframe(df4, use_container_width=True)
    with st.expander("Year-over-Year GMV"):
        df5 = q5_yoy(state_json)
        st.dataframe(df5, use_container_width=True)
        st.pyplot(yoy_chart(df5))

with tab_detail:
    # Insight
    st.markdown("""
    <div class="headline">
    <b>Insight:</b> Payment Instalments analysis shows most Credit Card Payment Type customers use 1 to 4 payment instalments, with a tail up to 24 payment instalments. 
    Higher payment instalments link to higher Average Payment Value — customers split expensive purchases. 
    When we filter by state, SP state shows higher use of payment instalments.
    </div>
    """, unsafe_allow_html=True)
    
    df6 = q6_instalments(selected_year, state_json)
    st.dataframe(df6, use_container_width=True)
    st.pyplot(instalment_chart(df6))
    
    st.markdown("---")
    # Dataset Limitation
    st.markdown("### Dataset Limitation")
    st.markdown(r"""
    **1. Incomplete Year Coverage:** 2016 has only Sep, Oct and Dec (no November) — 3 months. 2018 stops Oct 17. So Yearly GMV comparison is not balanced. We need full 12-month data for fair YoY.

    **2. Cancelled Orders in GMV:** Our Total GMV R\$15.8M includes 625 cancelled orders. So total is higher than actual Delivered GMV R\$15.4M. It is better to report Delivered GMV for true revenue.

    **3. No Customer Demographics:** We don't have age or income data. So we cannot analyze customer lifetime value or retention using payment type and state only.

    **4. State Concentration Risk:** 37.38% of Total GMV is from SP state alone. If SP logistics fails, one-third revenue is at risk. There's a need for growth in other states.

    **5. Freight Included in GMV:** Total GMV includes freight_value. Freight goes to logistics partner, not full margin for Olist. It is better to separate Item Revenue (R$13.5M) and Freight Revenue when reporting.
    """)