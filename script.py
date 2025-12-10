# -*- coding: utf-8 -*-
import requests
from datetime import datetime, timedelta
import urllib3
import os

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Telegram ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- Proxies Hong Kong / Singapore / EU (bypass US restriction) ---
PROXY_BASES = [
    "https://fapi.binancefuture.com",      # Hong Kong
    "https://binancefutures.moobie.tech",  # Singapore CDN
    "https://api.binanceproxy.cc",         # EU CDN
    "https://futures-api.binance.proxys.me",  # SG/HK Edge
    "https://api.binance.com"              # Fallback (US - may 451)
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BinanceTopRank/1.0)"}
ALLOWED_USD_QUOTES = {"USDT"}

# Time +7
utc_plus_7 = datetime.utcnow() + timedelta(hours=7)
timestamp_now = utc_plus_7.strftime("%Y-%m-%d %H:%M:%S")


# ===============================================================
#  FUNCTION: SAFE REQUEST THROUGH MULTIPLE PROXIES
# ===============================================================
def safe_get_json(path, timeout=20):
    """
    Tries multiple NON-US proxy endpoints until one works.
    """
    for base in PROXY_BASES:
        url = f"{base}{path}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
            r.raise_for_status()
            print(f"✅ SUCCESS via proxy: {base}")
            return r.json()
        except Exception as e:
            print(f"⚠️ Proxy failed {base}: {e}")

    print("❌ All proxies failed!")
    return None


# ===============================================================
#  GET SYMBOLS
# ===============================================================
def get_usdm_perp_symbols():
    data = safe_get_json("/fapi/v1/exchangeInfo")
    if not data:
        return set()

    symbols = set()
    for s in data.get("symbols", []):
        if (
            s.get("status") == "TRADING"
            and s.get("contractType") == "PERPETUAL"
            and s.get("quoteAsset") in ALLOWED_USD_QUOTES
        ):
            symbols.add(s["symbol"])
    return symbols


# ===============================================================
#  FILTER FUTURES +40%
# ===============================================================
def coins_up_over_40pct():
    allowed = get_usdm_perp_symbols()
    data = safe_get_json("/fapi/v1/ticker/24hr")

    if not data:
        return []

    rows = []
    for t in data:
        sym = t.get("symbol")
        if sym not in allowed:
            continue

        try:
            pct = float(t.get("priceChangePercent") or 0.0)
            last = float(t.get("lastPrice") or 0.0)
        except:
            continue

        if pct > 40:
            base = sym.replace("USDT", "")
            rows.append((sym, base, last, pct))

    rows.sort(key=lambda x: x[3], reverse=True)
    return rows


# ===============================================================
#  TELEGRAM
# ===============================================================
def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}

        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print("⚠️ Telegram error:", r.text)
        else:
            print("📨 Sent to Telegram")

    except Exception as e:
        print("❌ Telegram connection error:", e)


# ===============================================================
#  MAIN
# ===============================================================
def main():
    data = coins_up_over_40pct()

    if data:
        lines = [f"🚀 *Binance Futures >40% (non-US bypass)*\n⏰ {timestamp_now}"]
        for i, (sym, base, last, pct) in enumerate(data, 1):
            lines.append(f"{i}. {base} — #{sym}\nGiá: {last:.4f} | 24h: {pct:+.2f}%")
        msg = "\n".join(lines)
    else:
        msg = f"⏰ {timestamp_now}\n⚠️ Không có coin tăng >40% (or proxy failed)"

    send_telegram_message(msg)


if __name__ == "__main__":
    main()
