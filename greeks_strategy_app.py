import streamlit as st
import requests
import numpy as np
import math
from scipy.stats import norm
from bs4 import BeautifulSoup

st.set_page_config(page_title="Opsiyon Karar Destek Sistemi", layout="centered")
st.title("📈 Opsiyon Karar Destek Sistemi")

API_KEY = "8R9UWHCB38LG7G8R"
r = 0.05
sigma = 0.85

# Kullanıcıdan hisse kodu al
ticker = st.text_input("Hisse Kodu (örnek: OKLO)", value="OKLO")

# Güncel fiyat çekme
def get_stock_price(ticker):
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    try:
        return float(data["Global Quote"]["05. price"])
    except:
        return None

# Geçmiş fiyat verisi
def get_historical_prices(ticker):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&outputsize=compact&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    try:
        prices = [float(v["4. close"]) for k, v in sorted(data["Time Series (Daily)"].items(), reverse=False)]
        return prices[-60:]
    except:
        return None

# RSI hesaplama
def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed > 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)
    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        upval = max(delta, 0)
        downval = -min(delta, 0)
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    return rsi

# RSI Divergence
def detect_rsi_divergence(prices, rsi):
    price_trend = prices[-1] - prices[-14]
    rsi_trend = rsi[-1] - rsi[-14]
    if price_trend > 0 and rsi_trend < 0:
        return "negative"
    elif price_trend < 0 and rsi_trend > 0:
        return "positive"
    else:
        return "none"

# Yön önerisi
def suggest_direction(rsi_value, rsi_divergence, annual_return):
    if rsi_value > 70 and rsi_divergence == "negative":
        return "put"
    elif rsi_value < 30 and rsi_divergence == "positive":
        return "call"
    elif annual_return > 1000:
        return "put"
    else:
        return "neutral"

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

# Opsiyon zinciri scraper
def scrape_option_chain(ticker):
    url = f"https://www.barchart.com/stocks/quotes/{ticker}/options"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "lxml")
    options_data = []
    rows = soup.select("div .bc-table-scrollable table tbody tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 10:
            try:
                option = {
                    "Type": "Call" if "Call" in cells[0].text else "Put",
                    "Strike": float(cells[2].text.strip()),
                    "Last": float(cells[3].text.strip()),
                    "Bid": float(cells[4].text.strip()),
                    "Ask": float(cells[5].text.strip()),
                    "IV": cells[9].text.strip(),
                    "Delta": cells[10].text.strip() if len(cells) > 10 else "N/A"
                }
                options_data.append(option)
            except:
                continue
    return options_data

# Uygulama akışı
if ticker:
    price = get_stock_price(ticker)
    prices = get_historical_prices(ticker)

    if price is None:
        st.error("Hisse fiyatı alınamadı.")
    elif prices is None:
        st.error("Geçmiş fiyat verisi alınamadı.")
    else:
        st.success(f"{ticker} güncel fiyatı: ${price:.2f}")
        rsi = calculate_rsi(prices)
        rsi_value = rsi[-1]
        rsi_div = detect_rsi_divergence(prices, rsi)
        annual_return = ((prices[-1] / prices[0]) - 1) * 100
        direction = suggest_direction(rsi_value, rsi_div, annual_return)

        st.subheader("📊 Yön Önerisi")
        st.write(f"RSI: {rsi_value:.2f} | RSI Divergence: {rsi_div} | Yıllık Getiri: %{annual_return:.2f}")
        st.success(f"Önerilen yön: **{direction.upper()}** opsiyonu")

        if rsi_value > 80 or annual_return > 1000:
            st.warning("⚠️ Aşırı alım ve spekülatif yükseliş tespit edildi. PUT opsiyonu veya spread stratejileri değerlendirilebilir.")

        K = st.number_input("Kullanım Fiyatı (Strike)", value=round(price))
        days_to_expiry = st.number_input("Vade Süresi (Gün)", value=90)
        T = days_to_expiry / 365
        greeks = calculate_greeks(price, K, T, r, sigma, direction)

        st.subheader("📊 Greeks Sonuçları")
        for greek, value in greeks.items():
            st.write(f"**{greek}**: {value:.4f}")

        if st.button("🔍 En Uygun Opsiyon Pozisyonunu Göster"):
            st.subheader(f"{ticker} için Opsiyon Zinciri Analizi")
            try:
                chain = scrape_option_chain(ticker)
                filtered = [opt for opt in chain if opt["Type"].lower() == direction and opt["Delta"] != "N/A"]
                sorted_chain = sorted(filtered, key=lambda x: abs(float(x["Delta"]) - 0.8))
                if sorted_chain:
                    best = sorted_chain[0]
                    st.success(f"📌 Önerilen Pozisyon:\nTür: {best['Type']}\nStrike: ${best['Strike']}\nPrim: ${best['Ask']}\nIV: {best['IV']}\nDelta: {best['Delta']}")
                else:
                    st.warning("Uygun opsiyon pozisyonu bulunamadı.")
            except Exception as e:
                st.error(f"Hata oluştu: {e}")
