from typing import Dict, Any
from .base import VolumeEngine

class SideInferenceEngine(VolumeEngine):
    name = "side_inference"
    description = "Refina side usando padrões de preço (complementa side real da Binance)"
    
    def __init__(self):
        self.last_price = 0.0
    
    def calculate_volume_weight(self, tick: Dict[str, Any], context: Dict[str, Any]) -> float:
        return 1.0
    
    def infer_side(self, tick: Dict[str, Any], context: Dict[str, Any]) -> str:
        price = tick.get("price", 0.0)
        real_side = context.get("real_side", "neutral")
        
        if self.last_price == 0.0:
            self.last_price = price
            return real_side
        
        price_change = price - self.last_price
        abs_change = abs(price_change)
        
        if abs_change / self.last_price > 0.0005:
            inferred = "buy" if price_change > 0 else "sell"
            if inferred != real_side:
                real_side = inferred
        
        self.last_price = price
        return real_side