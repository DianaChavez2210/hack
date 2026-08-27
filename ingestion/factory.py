"""
Fábrica de Adaptadores de Ingesta (Factory Pattern).
Permite instanciar dinámicamente adaptadores para N centros de salud
sin acoplar el orquestador a implementaciones concretas.
"""

from typing import Dict, Type, List, Any
from ingestion.base_adapter import BaseHospitalAdapter


class HospitalIngestionFactory:
    """
    Fábrica y registro dinámico de adaptadores de ingesta.
    """
    _registry: Dict[str, Type[BaseHospitalAdapter]] = {}

    @classmethod
    def register(cls, source_type: str):
        """
        Decorador para registrar una clase de adaptador en la fábrica.
        """
        def decorator(subclass: Type[BaseHospitalAdapter]):
            cls._registry[source_type.upper()] = subclass
            return subclass
        return decorator

    @classmethod
    def register_adapter(cls, source_type: str, adapter_cls: Type[BaseHospitalAdapter]):
        """
        Registra programáticamente un adaptador en la fábrica.
        """
        cls._registry[source_type.upper()] = adapter_cls

    @classmethod
    def get_adapter(cls, source_type: str, hospital_id: str, source_name: str = "", **kwargs: Any) -> BaseHospitalAdapter:
        """
        Instancia y retorna el adaptador correspondiente al tipo de fuente.
        """
        key = source_type.upper()
        if key not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(f"Adaptador '{source_type}' no registrado. Disponibles: [{available}]")
        
        adapter_cls = cls._registry[key]
        return adapter_cls(hospital_id=hospital_id, source_name=source_name or source_type, **kwargs)

    @classmethod
    def list_available_adapters(cls) -> List[str]:
        """
        Retorna la lista de adaptadores registrados.
        """
        return list(cls._registry.keys())
