"""
Interfaz Abstracta para los Adaptadores de Ingesta por Hospital.
Aplica el principio de responsabilidad única (Single Responsibility Principle):
- extract_raw: lee el origen y genera la copia inmutable en RAW.
- map_to_cdm: transforma los registros al Common Data Model (CDM).
No contiene lógica de limpieza ni validación, la cual reside en el pipeline común.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ingestion.models import RawRecord, CDMRecord


class BaseHospitalAdapter(ABC):
    """
    Clase base abstracta para todos los adaptadores de hospitales y centros de salud.
    """
    def __init__(self, hospital_id: str, source_name: str):
        self.hospital_id = hospital_id
        self.source_name = source_name

    @abstractmethod
    def extract_raw(self, source_config: Dict[str, Any]) -> List[RawRecord]:
        """
        Extrae datos sin transformar desde el origen y genera objetos RawRecord.
        """
        pass

    @abstractmethod
    def map_to_cdm(self, raw_records: List[RawRecord]) -> List[CDMRecord]:
        """
        Mapea los registros RawRecord al Common Data Model (CDM) canónico.
        """
        pass
