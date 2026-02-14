from typing import Dict, Any, List
from .base import VolumeEngine
import time

class MicroClusterEngine(VolumeEngine):
    name = "micro_cluster"
    description = "Agrupa trades em janelas de 100ms para detectar micro-absorções"
    
    def __init__(self, window_ms: int = 100, absorption_threshold: float = 2.0):
        self.window_ms = window_ms / 1000.0
        self.absorption_threshold = absorption_threshold
        self.buffer: List[Dict[str, Any]] = []
        self.window_start = 0.0
        self.last_cluster = None
    
    def calculate_volume_weight(self, tick: Dict[str, Any], context: Dict[str, Any]) -> float:
        timestamp = tick.get("timestamp", time.time() * 1000) / 1000.0
        
        if self.window_start == 0.0:
            self.window_start = timestamp
        
        self.buffer.append({
            "price": tick.get("price", 0.0),
            "timestamp": timestamp,
            "side": context.get("real_side", "neutral"),
            "volume": tick.get("volume_real", 1.0),
        })
        
        window_elapsed = timestamp - self.window_start
        
        if window_elapsed >= self.window_ms and len(self.buffer) > 0:
            buy_vol = sum(t["volume"] for t in self.buffer if t["side"] == "buy")
            sell_vol = sum(t["volume"] for t in self.buffer if t["side"] == "sell")
            total_vol = buy_vol + sell_vol
            
            open_price = self.buffer[0]["price"]
            close_price = self.buffer[-1]["price"]
            price_change = close_price - open_price
            
            is_absorption = False
            absorption_type = None
            
            if price_change > 0 and sell_vol > buy_vol * self.absorption_threshold:
                is_absorption = True
                absorption_type = "buy"
            elif price_change < 0 and buy_vol > sell_vol * self.absorption_threshold:
                is_absorption = True
                absorption_type = "sell"
            
            base_factor = 1.8 if is_absorption else 1.0
            
            self.last_cluster = {
                "buy_volume": buy_vol,
                "sell_volume": sell_vol,
                "is_absorption": is_absorption,
                "absorption_type": absorption_type,
                "price_change": price_change,
                "timestamp": timestamp,
            }
            
            self.buffer.clear()
            self.window_start = timestamp
            
            return min(base_factor, 2.0)
        
        return 1.0
    
    def infer_side(self, tick: Dict[str, Any], context: Dict[str, Any]) -> str:
        if self.last_cluster and self.last_cluster["is_absorption"]:
            if self.last_cluster["absorption_type"] == "buy":
                return "sell"
            elif self.last_cluster["absorption_type"] == "sell":
                return "buy"
        
        return context.get("real_side", "neutral")