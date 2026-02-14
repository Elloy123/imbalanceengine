import time
from typing import Dict, Any
from .base import VolumeEngine

class TickVelocityEngine(VolumeEngine):
    name = "tick_velocity"
    description = "Pondera volume pela velocidade dos trades (trades rápidos = mais volume)"
    
    def __init__(self):
        self.last_trade_time = time.time()
        self.min_interval = 0.001
    
    def calculate_volume_weight(self, tick: Dict[str, Any], context: Dict[str, Any]) -> float:
        now = time.time()
        interval = max(now - self.last_trade_time, self.min_interval)
        self.last_trade_time = now
        
        velocity = min(1.0 / interval, 50.0)
        normalized = min(velocity / 25.0, 1.0)
        return max(normalized, 0.1)
    
    def infer_side(self, tick: Dict[str, Any], context: Dict[str, Any]) -> str:
        return context.get("real_side", "neutral")