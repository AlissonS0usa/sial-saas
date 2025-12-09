from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, Dict

class UsuarioBrief(BaseModel):
    id: UUID
    nome: str
    class Config:
        from_attributes = True

class LugarBrief(BaseModel):
    id: UUID
    nome: str
    usuario: Optional[UsuarioBrief] = None
    class Config:
        from_attributes = True

class DispositivoBase(BaseModel):
    nome: str
    localizacao: Optional[str] = None
    lugar_id: UUID
    tipo: str                               # ex: "umidificador_ar", "sensor_solo"
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

class DispositivoCreate(DispositivoBase):
    pass

class DispositivoUpdateLugar(BaseModel):
    lugar_id: UUID

class DispositivoComandoIn(BaseModel):
    acao: str

class DispositivoOut(DispositivoBase):
    id: UUID
    ativo: bool
    criado_em: datetime
    lugar: Optional[LugarBrief] = None

    class Config:
        from_attributes = True
