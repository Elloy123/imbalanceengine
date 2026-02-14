# C:\imbalanceengine\backend\test_binance.py
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    price = float(data['p'])
    volume = float(data['q']) * price
    side = "BUY" if not data['m'] else "SELL"
    print(f"BTC/USDT | {price:,.2f} | ${volume:,.0f} | {side}")

ws = websocket.WebSocketApp(
    "wss://stream.binance.com:9443/ws/btcusdt@trade",
    on_message=on_message
)
ws.run_forever()