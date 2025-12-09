
from uuid import UUID
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

class LeituraOut(BaseModel):
    id: UUID
    dispositivo_id: UUID
    dados: Dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True

class PontoUmidade(BaseModel):
    timestamp: datetime
    umidade: float


class SeriesRelatorioDispositivo(BaseModel):
    umidade: List[PontoUmidade]


class RelatorioDispositivoMetricas(BaseModel):
    umidade_min: Optional[float] = None
    umidade_max: Optional[float] = None
    umidade_media: Optional[float] = None

    leituras_total: int
    leituras_com_umidade: int

    dentro_faixa: Optional[int] = None
    fora_faixa: Optional[int] = None
    percentual_dentro_faixa: Optional[float] = None


class RelatorioDispositivoOut(BaseModel):
    dispositivo: Dict[str, Any]
    periodo: Dict[str, datetime]
    parametros_alvo: Dict[str, Optional[float]]
    metricas: RelatorioDispositivoMetricas
    series: SeriesRelatorioDispositivo
