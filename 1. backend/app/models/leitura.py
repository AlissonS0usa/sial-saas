import uuid
from sqlalchemy import Column, Float, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Leitura(Base):
    __tablename__ = "leituras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    dispositivo_id = Column(UUID(as_uuid=True), ForeignKey("dispositivos.id"), nullable=False)
    dispositivo = relationship("Dispositivo")

    dados = Column(JSONB, nullable=False)            # ex: {"umidade":71.4,"temperatura":25.6,"status":"ligado","potencia":2}
    timestamp = Column(DateTime, default=datetime.utcnow)
