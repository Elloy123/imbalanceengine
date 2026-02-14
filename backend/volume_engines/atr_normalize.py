from typing import Dict, Any
from .base import VolumeEngine

class ATRNormalizeEngine(VolumeEngine):
    name = "atr_normalize"
    description = "Normaliza volume pela volatilidade (ATR simplificado para BTC)"
    
    def __init__(self):
        self.price_history = []
        self.max_history = 14
        self.atr_baseline = 150.0
    
    def calculate_volume_weight(self, tick: Dict[str, Any], context: Dict[str, Any]) -> float:
        price = tick.get("price", 0.0)
        self.price_history.append(price)
        
        if len(self.price_history) > self.max_history + 1:
            self.price_history.pop(0)
        
        if len(self.price_history) < self.max_history + 1:
            return 1.0
        
        tr_values = []
        for i in range(1, len(self.price_history)):
            high = max(self.price_history[i], self.price_history[i-1])
            low = min(self.price_history[i], self.price_history[i-1])
            tr = high - low
            tr_values.append(tr)
        
        atr = sum(tr_values[-self.max_history:]) / self.max_history
        atr_ratio = atr / self.atr_baseline
        
        weight = 1.0 / max(atr_ratio, 0.5)
        return min(weight, 2.0)
    
    def infer_side(self, tick: Dict[str, Any], context: Dict[str, Any]) -> str:
        return context.get("real_side", "neutral")