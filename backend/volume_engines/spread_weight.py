from typing import Dict, Any
from .base import VolumeEngine

class SpreadWeightEngine(VolumeEngine):
    name = "spread_weight"
    description = "Ajusta volume conforme volatilidade recente (simula spread)"
    
    def __init__(self):
        self.price_history = []
        self.max_history = 20
    
    def calculate_volume_weight(self, tick: Dict[str, Any], context: Dict[str, Any]) -> float:
        price = tick.get("price", 0.0)
        self.price_history.append(price)
        
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)
        
        if len(self.price_history) < 5:
            return 1.0
        
        avg = sum(self.price_history) / len(self.price_history)
        variance = sum((p - avg) ** 2 for p in self.price_history) / len(self.price_history)
        volatility = variance ** 0.5
        
        normalized_vol = min(volatility / 100.0, 1.5)
        weight = 1.0 / max(normalized_vol, 0.5)
        return min(max(weight * 0.8 + 0.2, 0.3), 1.5)
    
    def infer_side(self, tick: Dict[str, Any], context: Dict[str, Any]) -> str:
        return context.get("real_side", "neutral")