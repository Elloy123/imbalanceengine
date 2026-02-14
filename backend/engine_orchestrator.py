from typing import List, Dict, Any
from volume_engines.base import VolumeEngine
from volume_engines import (
    TickVelocityEngine,
    SpreadWeightEngine,
    SideInferenceEngine,
    MicroClusterEngine,
    ATRNormalizeEngine,
)

ENGINE_REGISTRY = {
    "tick_velocity": TickVelocityEngine,
    "spread_weight": SpreadWeightEngine,
    "side_inference": SideInferenceEngine,
    "micro_cluster": MicroClusterEngine,
    "atr_normalize": ATRNormalizeEngine,
}

class VolumeEngineOrchestrator:
    def __init__(self, engine_names: List[str], weights: Dict[str, float] = None):
        self.engines: List[VolumeEngine] = []
        self.tick_count = 0
        
        for name in engine_names:
            if name not in ENGINE_REGISTRY:
                raise ValueError(f"Engine desconhecido: {name}")
            self.engines.append(ENGINE_REGISTRY[name]())
        
        self.weights = weights or {name: 1.0 / len(engine_names) for name in engine_names}
    
    def calculate_enhanced_volume(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        self.tick_count += 1
        
        context = {
            "tick_count": self.tick_count,
            "real_side": tick.get("side_real", "neutral"),
            "real_volume": tick.get("volume_real", 1.0),
            "price": tick.get("price", 0.0),
            "last_price": getattr(self, 'last_price', 0.0),
        }
        
        side = tick.get("side_real", "neutral")
        for engine in self.engines:
            if engine.name == "side_inference":
                side = engine.infer_side(tick, context)
                break
        
        weight_factors = []
        engine_contributions = {}
        
        for engine in self.engines:
            if engine.name == "side_inference":
                continue
            
            weight = self.weights.get(engine.name, 1.0 / len(self.engines))
            factor = engine.calculate_volume_weight(tick, context)
            weighted_factor = factor * weight
            weight_factors.append(weighted_factor)
            engine_contributions[engine.name] = round(weighted_factor, 3)
        
        avg_factor = sum(weight_factors) / len(weight_factors) if weight_factors else 1.0
        
        base_volume = tick.get("volume_real", 100.0)
        enhanced_volume = base_volume * avg_factor
        
        self.last_price = tick.get("price", 0.0)
        
        return {
            "volume": round(enhanced_volume, 2),
            "side": side,
            "engine_contributions": engine_contributions,
            "is_absorption": engine_contributions.get("micro_cluster", 0) > 1.5,
            "timestamp": tick.get("timestamp", 0),
            "price": tick.get("price", 0.0),
        }
    
    def get_active_engines(self) -> List[Dict[str, str]]:
        return [
            {"id": engine.name, "description": engine.description}
            for engine in self.engines
        ]