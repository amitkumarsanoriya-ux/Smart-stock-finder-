import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Smart Stock Finder PRO",
    page_icon="📈",
    layout="wide"
)

st.title("📈 SMART STOCK FINDER PRO")
st.caption("NSE Fundamental + Technical Stock Analysis")

st.sidebar.header("Settings")
minimum = st.sidebar.slider("Minimum Stock Score", 0, 100, 65)

st.info("Upload Screener CSV and daily price data to analyse stocks.")

fund_file = st.file_uploader(
    "Upload Screener Fundamentals CSV",
    type=["csv"]
)

price_file = st.file_uploader(
    "Upload Daily OHLCV CSV",
    type=["csv"]
)

def score_fundamental(row):
    score = 0

    def val(name):
        try:
            return float(row[name])
        except:
            return 0

    if val("Sales growth") >= 15:
        score += 10

    if val("Profit growth") >= 15:
        score += 15

    if val("ROCE") >= 15:
        score += 12

    if val("ROE") >= 15:
        score += 8

    if val("OPM") >= 12:
        score += 7

    if val("Debt to equity") <= 0.5:
        score += 8

    return score

def analyse_technical(g):
    g = g.sort_values("Date").copy()

    c = g["Close"]

    g["EMA8"] = c.ewm(span=8).mean()
    g["EMA20"] = c.ewm(span=20).mean()
    g["EMA7"] = c.ewm(span=7).mean()
    g["EMA21"] = c.ewm(span=21).mean()

    delta = c.diff()
    gain = delta.clip(lower=0).ewm(span=14).mean()
    loss = (-delta.clip(upper=0)).ewm(span=14).mean()

    rs = gain / loss.replace(0, np.nan)
    g["RSI"] = 100 - (100 / (1 + rs))

    last = g.iloc[-1]
    score = 0

    if last["EMA8"] > last["EMA20"]:
        score += 10

    if last["EMA7"] > last["EMA21"]:
        score += 10

    if last["RSI"] > 50 and last["RSI"] < 70:
        score += 10

    if last["Close"] > g["Close"].rolling(20).mean().iloc[-1]:
        score += 10

    return pd.Series({
        "Technical Score": score,
        "Close": last["Close"],
        "RSI": last["RSI"]
    })

if fund_file and price_file:

    f = pd.read_csv(fund_file)
    p = pd.read_csv(price_file)

    required = [
        "Date", "Symbol", "Open",
        "High", "Low", "Close", "Volume"
    ]

    if not all(x in p.columns for x in required):
        st.error("Price CSV columns are incorrect.")
        st.stop()

    if "Symbol" not in f.columns:
        st.error("Fundamental CSV must contain Symbol column.")
        st.stop()

    f["Symbol"] = f["Symbol"].astype(str).str.upper()
    p["Symbol"] = p["Symbol"].astype(str).str.upper()

    f = f.drop_duplicates("Symbol")

    f["Fundamental Score"] = f.apply(
        score_fundamental, axis=1
    )

    p["Date"] = pd.to_datetime(p["Date"])

    tech = []

    for symbol, group in p.groupby("Symbol"):
        result = analyse_technical(group)
        result["Symbol"] = symbol
        tech.append(result)

    t = pd.DataFrame(tech)

    final = f.merge(t, on="Symbol", how="inner")

    final["Total Score"] = (
        final["Fundamental Score"] * 0.6
        + final["Technical Score"]
    ).round(1)

    final = final.sort_values(
        "Total Score", ascending=False
    )

    final["Classification"] = np.where(
        final["Total Score"] >= 80,
        "High Priority",
        np.where(
            final["Total Score"] >= 65,
            "Watchlist",
            "Further Research"
        )
    )

    result = final[
        final["Total Score"] >= minimum
    ]

    a, b, c = st.columns(3)

    a.metric("Stocks Analysed", len(final))
    b.metric("Shortlisted", len(result))
    c.metric("Average Score", round(final["Total Score"].mean(), 1))

    st.subheader("🏆 FINAL STOCK RANKING")

    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download Stock List",
        final.to_csv(index=False).encode("utf-8"),
        "stock_ranking.csv"
    )

else:
    st.warning(
        "Please upload both CSV files to start analysis."
    )
