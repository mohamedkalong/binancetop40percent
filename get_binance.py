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

# --- Telegram ---
#TELEGRAM_TOKEN = "8219004391:AAEyCr89eR33w17-fikVUm3-xYnok1oahRY"
#CHAT_ID = "5235344133"

PROXIES = {
    'http': os.getenv('HTTP_PROXY'),  # Lưu proxy trong GitHub Secrets
    'https': os.getenv('HTTPS_PROXY')
}

# --- Binance ---
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TopRankScraper/1.0)"}
ALLOWED_USD_QUOTES = {"USDT"}
BINANCE_API_BASE = "https://fapi.binance.com"   # hoạt động tốt trên PythonAnywhere

# Time +7
utc_now = datetime.now()
utc_plus_7 = utc_now + timedelta(hours=7)
result = utc_plus_7.strftime("%Y-%m-%d, %H:%M:%S")


def get_usdm_perp_symbols():
    """Lấy danh sách symbol USDT-M PERPETUAL đang TRADING"""
    try:
        resp = requests.get(f"{BINANCE_API_BASE}/fapi/v1/exchangeInfo", headers=HEADERS, timeout=20, proxies=PROXIES)
        resp.raise_for_status()
        info = resp.json()
    except Exception as e:
        print("❌ Lỗi khi lấy danh sách symbol:", e)
        return set()

    symbols = set()
    for s in info.get("symbols", []):
        if (
            s.get("status") == "TRADING"
            and s.get("contractType") == "PERPETUAL"
            and s.get("quoteAsset") in ALLOWED_USD_QUOTES
        ):
            symbols.add(s["symbol"])
    return symbols


def coins_up_over_40pct():
    """Lọc coin USDT-M Futures tăng >40% trong 24h"""
    allowed = get_usdm_perp_symbols()

    try:
        resp = requests.get(f"{BINANCE_API_BASE}/fapi/v1/ticker/24hr", headers=HEADERS, timeout=25, proxies=PROXIES)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print("❌ Lỗi khi gọi API Binance:", e)
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

        # 🔥 Chỉ lấy coin tăng hơn 40%
        if pct > 40:
            base = sym.replace("USDT", "")
            rows.append((sym, base, last, pct))

    # Sắp xếp từ tăng mạnh nhất xuống thấp hơn
    rows.sort(key=lambda x: x[3], reverse=True)
    return rows


def send_telegram_message(text):
    """Send Telegram message"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            print("⚠️ Lỗi gửi Telegram:", resp.text)
        else:
            print("✅ Đã gửi kết quả lên Telegram")
    except Exception as e:
        print("❌ Lỗi kết nối Telegram:", e)


def main():
    utc_now = datetime.now()
    utc_plus_7 = utc_now + timedelta(hours=7)
    now = utc_plus_7.strftime("%Y-%m-%d, %H:%M:%S")  # Thay vì now = result
    fut = coins_up_over_40pct()
    
    if fut:
        message_lines = [f"🚀 *Binance Futures >40% (USDT)* - via pythonganywhere\n⏰ {now}"]
        for i, (sym, base, last, pct) in enumerate(fut, 1):
            message_lines.append(
                f"{i}. {base} — #{sym} | Giá: {last:.4f} | 24h: {pct:+.2f}%"
            )
        message = "\n".join(message_lines)
        send_telegram_message(message)
    else:
        send_telegram_message(f"⏰ {now}.\n⚠️ KhôKhông có coin nào tăng >40% trong 24h - pythonanywhere")

if __name__ == "__main__":
    main()
