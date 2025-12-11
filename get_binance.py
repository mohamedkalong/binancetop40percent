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

# --- Binance ---
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TopRankScraper/1.0; +https://example.local)"}
ALLOWED_USD_QUOTES = {"USDT"}
BINANCE_API_BASE = "https://fapi.binance.com"   # dùng domain chính, SSL hợp lệ


# ==============================
def get_usdm_perp_symbols():
    """Lấy danh sách symbol PERPETUAL đang TRADING"""
    try:
        resp = requests.get(f"{BINANCE_API_BASE}/fapi/v1/exchangeInfo", headers=HEADERS, timeout=20)
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


def top_gainers_usdm(limit=10):
    allowed = get_usdm_perp_symbols()
    try:
        resp = requests.get(f"{BINANCE_API_BASE}/fapi/v1/ticker/24hr", headers=HEADERS, timeout=25)
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
        except (TypeError, ValueError):
            continue

        base = sym[:-4] if sym.endswith("USDT") else sym
        rows.append((sym, base, last, pct))

    rows.sort(key=lambda x: x[3], reverse=True)
    return rows[:limit]


def send_telegram_message(text):
    """Gửi tin nhắn Telegram."""
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
    fut = top_gainers_usdm(limit=10)
    now = result

    if fut:
        message_lines = [f"🚀 *Top 10 Gainers Binance Futures (USDT)*\n⏰ {now}"]
        for i, (sym, base, last, pct) in enumerate(fut, 1):
            message_lines.append(f"{i}. {base} Perpetual — #{sym}\nGiá: {last:.4f} | 24h: {pct:+.2f}%")
        message = "\n".join(message_lines)
        send_telegram_message(message)
    else:
        send_telegram_message("⚠️ Không lấy được dữ liệu từ Binance.")


if __name__ == "__main__":
    main()
