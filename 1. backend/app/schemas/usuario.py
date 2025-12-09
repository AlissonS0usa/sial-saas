from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr
    role: str = "CLIENTE"

class UsuarioCreate(UsuarioBase):
    senha: str

class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    role: Optional[str] = None
    ativo: Optional[bool] = None

class UsuarioUpdateMe(BaseModel):
    nome: Optional[str] = Field(None, description="Novo nome do usuário")
    email: Optional[EmailStr] = Field(None, description="Novo e-mail do usuário")


class AlterarSenhaRequest(BaseModel):
    senha_atual: str = Field(..., min_length=1)
    nova_senha: str = Field(..., min_length=8, description="Nova senha (mínimo 8 caracteres)")

class UsuarioOut(UsuarioBase):
    id: UUID
    ativo: bool
    criado_em: datetime

    class Config:
        from_attributes = True
