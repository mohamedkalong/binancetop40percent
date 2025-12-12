# -*- coding: utf-8 -*-
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# --- Telegram config (lưu vào GitHub Secrets hoặc env) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# --- Binance Spot API (no proxy needed) ---
BINANCE_API_BASE = "https://api.binance.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RSIScraper/1.0)"}

def get_usdt_spot_symbols():
    """Lấy danh sách symbols spot USDT đang TRADING"""
    try:
        resp = requests.get(f"{BINANCE_API_BASE}/api/v3/exchangeInfo", headers=HEADERS, timeout=20)
        resp.raise_for_status()
        info = resp.json()
    except Exception as e:
        print(f"❌ Lỗi lấy exchangeInfo: {e}")
        return []

    symbols = []
    for s in info.get("symbols", []):
        if (s.get("status") == "TRADING" and
            s.get("quoteAsset") == "USDT" and
            s.get("symbol").endswith("USDT")):  # Chỉ spot USDT pairs
            symbols.append(s["symbol"])
    return symbols

def calculate_rsi(closes, period=14):
    """Tính RSI từ list close prices (sử dụng pandas)"""
    closes = pd.Series(closes)
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]  # RSI mới nhất

def get_rsi_for_symbol(symbol):
    """Lấy klines 1h và tính RSI cho symbol"""
    params = {
        "symbol": symbol,
        "interval": "1h",
        "limit": 15  # 14 periods + 1 current
    }
    try:
        resp = requests.get(f"{BINANCE_API_BASE}/api/v3/klines", headers=HEADERS, timeout=10, params=params)
        resp.raise_for_status()
        klines = resp.json()
        closes = [float(k[4]) for k in klines]  # Close prices
        if len(closes) < 15:
            return None
        rsi = calculate_rsi(closes)
        return rsi
    except Exception as e:
        print(f"❌ Lỗi lấy klines cho {symbol}: {e}")
        return None

def send_telegram_message(text):
    """Gửi message đến Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("✅ Đã gửi Telegram")
        else:
            print(f"⚠️ Lỗi gửi Telegram: {resp.text}")
    except Exception as e:
        print(f"❌ Lỗi kết nối Telegram: {e}")

def main():
    # Thời gian +7 (VN)
    utc_now = datetime.now()
    now = (utc_now + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
    
    symbols = get_usdt_spot_symbols()
    if not symbols:
        send_telegram_message(f"⏰ {now}\n❌ Lỗi lấy symbols spot - Không có dữ liệu.")
        return
    
    over_80 = []
    for symbol in symbols:
        rsi = get_rsi_for_symbol(symbol)
        if rsi is not None and rsi > 80:
            over_80.append((symbol, rsi))
    
    if over_80:
        # Sắp xếp theo RSI giảm dần
        over_80.sort(key=lambda x: x[1], reverse=True)
        message_lines = [f"🚨 *Coin RSI >80 (1h frame) - Binance Spot/Margin*\n⏰ {now}"]
        for i, (sym, rsi_val) in enumerate(over_80, 1):
            base = sym.replace("USDT", "")
            message_lines.append(f"{i}. {base} ({sym}) | RSI: {rsi_val:.2f}")
        message = "\n".join(message_lines)
        send_telegram_message(message)
    else:
        send_telegram_message(f"⏰ {now}\n✅ Không có coin nào RSI >80 trên khung 1h (Spot).")

if __name__ == "__main__":
    main()
