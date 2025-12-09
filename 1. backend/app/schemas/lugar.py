from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.schemas.usuario import UsuarioOut

class LugarBase(BaseModel):
    nome: str
    cep: Optional[str] = None
    rua: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    complemento: Optional[str] = None
    

class LugarCreate(LugarBase):
    usuario_id: Optional[UUID] = None

class LugarUpdate(LugarBase):
    usuario_id: Optional[UUID] = None

class LugarOut(LugarBase):
    id: UUID
    ativo: bool
    usuario: Optional[UsuarioOut] = None
    
    class Config:
        from_attributes = True
