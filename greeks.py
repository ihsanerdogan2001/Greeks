import math
from scipy.stats import norm

def black_scholes_greeks(S, K, T, r, sigma, option_type='call'):
    """
    S: Hisse fiyatı
    K: Kullanım fiyatı (strike)
    T: Vade süresi (yıl cinsinden)
    r: Risksiz faiz oranı
    sigma: Volatilite (standart sapma)
    option_type: 'call' veya 'put'
    """
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
        'Vega': vega / 100,  # Genellikle % değişim için bölünür
        'Rho': rho / 100
    }

# Örnek kullanım
greeks = black_scholes_greeks(S=100, K=100, T=1, r=0.05, sigma=0.2, option_type='call')
for greek, value in greeks.items():
    print(f"{greek}: {value:.4f}")
