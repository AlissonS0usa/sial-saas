import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Lugar(Base):
    __tablename__ = "lugares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nome = Column(String, nullable=False)
    cep = Column(String, nullable=False)
    rua = Column(String, nullable=False)
    numero = Column(String, nullable=False)
    bairro = Column(String, nullable=False)
    cidade = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    complemento = Column(String, nullable=True)

    ativo = Column(Boolean, default=True)

    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    usuario = relationship("Usuario")

    criado_em = Column(DateTime, default=datetime.utcnow)
