import asyncio
import websockets
import json
import time
from engine_orchestrator import VolumeEngineOrchestrator

class BinanceDataFeed:
    def __init__(self, symbol: str = "btcusdt", orchestrator: VolumeEngineOrchestrator = None):
        self.symbol = symbol.lower()
        self.orchestrator = orchestrator
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@trade"
        self.running = False
        self.trade_count = 0
        self.last_price = 0.0
    
    async def connect(self, on_data_callback=None):
        self.running = True
        print(f"🔌 Conectando à Binance: {self.symbol.upper()}")
        print(f"📡 WebSocket: {self.ws_url}\n")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print(f"✅ Conectado! Recebendo trades em tempo real...\n")
                print(f"{'Hora (UTC)':<12} | {'Preço':<12} | {'Volume':<12} | {'Side':<6} | {'Trade #'}")
                print("-" * 65)
                
                while self.running:
                    message = await websocket.recv()
                    data = json.loads(message)
                    await self._process_trade(data, on_data_callback)
        
        except Exception as e:
            print(f"❌ Erro WebSocket: {e}")
            await asyncio.sleep(5)
            await self.connect(on_data_callback)
    
    async def _process_trade(self, data: dict, on_data_callback=None):
        self.trade_count += 1
        
        price = float(data['p'])
        volume_btc = float(data['q'])
        volume_usdt = price * volume_btc
        is_maker = data['m']  # True = sell market order, False = buy market order
        timestamp = data['T']
        
        # Side REAL da Binance:
        # - is_maker=False → comprador agressivo (comprou no ask) → BUY
        # - is_maker=True  → vendedor agressivo (vendeu no bid) → SELL
        side_real = "buy" if not is_maker else "sell"
        
        # Cria tick compatível com engines
        tick = {
            "price": price,
            "bid": price - 0.05,
            "ask": price + 0.05,
            "last_bid": self.last_price - 0.05 if self.last_price else price - 0.05,
            "last_ask": self.last_price + 0.05 if self.last_price else price + 0.05,
            "timestamp": timestamp,
            "volume_real": volume_usdt,
            "side_real": side_real,
            "trade_id": data['t'],
        }
        
        self.last_price = price
        
        # Processa com engines se disponível
        enhanced = None
        if self.orchestrator:
            enhanced = self.orchestrator.calculate_enhanced_volume(tick)
        
        # Callback para frontend/salvamento
        if on_data_callback:
            payload = {
                "type": "trade",
                "symbol": self.symbol.upper(),
                "price": price,
                "volume_raw": volume_usdt,
                "volume": enhanced["volume"] if enhanced else volume_usdt,
                "side": enhanced["side"] if enhanced else side_real,
                "side_real": side_real,
                "timestamp": timestamp,
                "is_absorption": enhanced.get("is_absorption", False) if enhanced else False,
                "engine_contributions": enhanced.get("engine_contributions", {}) if enhanced else {},
                "trade_count": self.trade_count,
            }
            await on_data_callback(payload)
        
        # Mostra no console
        now = time.strftime('%H:%M:%S', time.gmtime(timestamp/1000))
        side_color = "\033[92mBUY \033[0m" if side_real == "buy" else "\033[91mSELL\033[0m"
        vol_display = f"{enhanced['volume']:.0f}" if enhanced else f"{volume_usdt:.0f}"
        print(f"{now:<12} | {price:<12.2f} | {vol_display:<12} | {side_color} | #{self.trade_count}")
    
    def stop(self):
        self.running = False
        print("\n⏹️  Conexão encerrada")

# Teste rápido independente (execute: python binance_ws.py)
if __name__ == "__main__":
    async def dummy_handler(data):
        pass  # Só mostra no console
    
    orchestrator = VolumeEngineOrchestrator(
        engine_names=["tick_velocity", "side_inference", "micro_cluster"],
        weights={"tick_velocity": 1.0, "side_inference": 1.0, "micro_cluster": 1.5}
    )
    
    feed = BinanceDataFeed(symbol="btcusdt", orchestrator=orchestrator)
    
    try:
        asyncio.run(feed.connect(dummy_handler))
    except KeyboardInterrupt:
        feed.stop()
        print("\n👋 Até logo!")