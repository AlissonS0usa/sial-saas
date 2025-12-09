import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Dispositivo(Base):
    __tablename__ = "dispositivos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nome = Column(String, nullable=False)
    localizacao = Column(String, nullable=True)

    lugar_id = Column(UUID(as_uuid=True), ForeignKey("lugares.id"), nullable=False)
    lugar = relationship("Lugar")

    tipo = Column(String, nullable=False)            # ex: "umidificador_ar", "sensor_solo", "termometro"
    status = Column(String, nullable=True)           # ex: "online", "offline"
    config = Column(JSONB, nullable=True)            # ex: {"umidade_min":65,"umidade_max":75,"potencia":2}

    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
