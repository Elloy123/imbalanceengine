from abc import ABC, abstractmethod
from typing import Dict, Any

class VolumeEngine(ABC):
    name: str = "base"
    description: str = "Engine base"
    
    @abstractmethod
    def calculate_volume_weight(self, tick: Dict[str, Any], context: Dict[str, Any]) -> float:
        pass
    
    @abstractmethod
    def infer_side(self, tick: Dict[str, Any], context: Dict[str, Any]) -> str:
        pass