import streamlit as st
import requests
import math
import numpy as np
import pandas as pd
from scipy.stats import norm
import plotly.express as px

# Sayfa ayarları
st.set_page_config(page_title="Opsiyon Analiz Platformu", layout="centered")
st.title("📈 Opsiyon Analiz Platformu")

# API ayarları
API_KEY = "8R9UWHCB38LG7G8R"
r = 0.05  # Sabit risksiz faiz oranı
sigma = 0.85  # Şimdilik sabit volatilite

# Hisse kodu girişi
ticker = st.text_input("Hisse Kodu (örnek: OKLO)", value="OKLO")

# Güncel fiyat çekme
def get_stock_price(ticker):
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    try:
        price = float(data["Global Quote"]["05. price"])
        return price
    except:
        return None

# Geçmiş fiyat verisi çekme
def get_historical_prices(ticker):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize=compact&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    try:
        prices = [float(v["4. close"]) for k, v in sorted(data["Time Series (Daily)"].items(), reverse=False)]
        return prices[-30:]
    except:
        return None

# Trend analizi
def analyze_trend(prices):
    returns = np.diff(prices)
    avg_return = np.mean(returns)
    if avg_return > 0:
        return "call", avg_return
    else:
        return "put", avg_return

# Greeks hesaplama
def calculate_greeks(S, K, T, r, sigma, option_type):
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == 'call':
        delta = norm.cdf(d1)
        theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T))) - r * K * math.exp(-r * T) * norm.cdf(d2)
        rho = K * T * math.exp(-r * T) * norm.cdf(d2)
    else:
        delta = -norm.cdf(-d1)
        theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T))) + r * K * math.exp(-r * T) * norm.cdf(-d2)
        rho = -K * T * math.exp(-r * T) * norm.cdf(-d2)

    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * norm.pdf(d1) * math.sqrt(T)

    return {
        'Delta': delta,
        'Gamma': gamma,
        'Theta': theta,
        'Vega': vega / 100,
        'Rho': rho / 100
    }

# Simülasyon
def simulate_combinations(S, r, sigma, option_type):
    results = []
    for K in range(int(S * 0.8), int(S * 1.2), 5):
        for days in range(30, 181, 30):
            T = days / 365
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)

            if option_type == 'call':
                delta = norm.cdf(d1)
                theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T))) - r * K * math.exp(-r * T) * norm.cdf(d2)
            else:
                delta = -norm.cdf(-d1)
                theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T))) + r * K * math.exp(-r * T) * norm.cdf(-d2)

            gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
            vega = S * norm.pdf(d1) * math.sqrt(T) / 100

            results.append({
                "Strike": K,
                "Vade (gün)": days,
                "Delta": delta,
                "Theta": theta,
                "Vega": vega
            })

    return pd.DataFrame(results)

# Uygulama akışı
if ticker:
    price = get_stock_price(ticker)
    prices = get_historical_prices(ticker)

    if price:
        st.success(f"{ticker} güncel fiyatı: ${price:.2f}")
        st.info(f"Risksiz faiz oranı (r): {r:.2f}")
        if prices:
            direction, momentum = analyze_trend(prices)
            st.subheader("📊 Opsiyon Yönü Önerisi")
            st.write(f"Son 30 günlük ortalama momentum: {momentum:.2f}")
            st.success(f"Önerilen yön: **{direction.upper()}** opsiyonu")

            # Greeks hesaplama
            K = st.number_input("Kullanım Fiyatı (Strike)", value=100.0)
            days_to_expiry = st.number_input("Vade Süresi (Gün)", value=90)
            T = days_to_expiry / 365

            greeks = calculate_greeks(price, K, T, r, sigma, direction)
            st.subheader("📊 Greeks Sonuçları")
            for greek, value in greeks.items():
                st.write(f"**{greek}**: {value:.4f}")

            # Simülasyon ve öneri
            st.subheader("🔍 Vade ve Strike Simülasyonu")
            df = simulate_combinations(price, r, sigma, direction)
            st.dataframe(df)

            filtered = df[(df["Delta"] > 0.8) & (df["Theta"] > -2)]
            if not filtered.empty:
                best = filtered.iloc[0]
                st.success(f"📌 Önerilen Kombinasyon:\nStrike: {best['Strike']} USD\nVade: {best['Vade (gün)']} gün\nDelta: {best['Delta']:.2f}\nTheta: {best['Theta']:.2f}")
            else:
                st.warning("Belirtilen kriterlere uygun kombinasyon bulunamadı.")

            # Grafikler
            st.subheader("📈 Grafiksel Analiz")
            fig_vega = px.line(df, x="Strike", y="Vega", title="Vega vs Strike")
            st.plotly_chart(fig_vega)

            fig_theta = px.line(df, x="Vade (gün)", y="Theta", title="Theta vs Vade")
            st.plotly_chart(fig_theta)

            fig_delta = px.line(df, x="Strike", y="Delta", title="Delta vs Strike")
            st.plotly_chart(fig_delta)
        else:
            st.error("Geçmiş fiyat verisi alınamadı.")
    else:
        st.error("Güncel fiyat verisi alınamadı.")
