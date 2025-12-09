# app/services/mqtt_telemetria.py (por exemplo)
import json
from typing import Optional

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.dispositivo import Dispositivo
from app.models.leitura import Leitura

def encontrar_dispositivo_por_base_topic(db: Session, base_topic: str) -> Optional[Dispositivo]:
    """
    Procura o dispositivo cujo config.mqtt.baseTopic == base_topic
    (adapte o acesso ao JSON conforme seu setup de SQLAlchemy).
    """
    # Exemplo genérico, você ajusta para o seu dialect:
    # Dispositivo.config["mqtt"]["baseTopic"].astext == base_topic
    return (
        db.query(Dispositivo)
        .filter(Dispositivo.config["mqtt"]["baseTopic"].astext == base_topic)
        .first()
    )

def processar_telemetria(topic: str, payload: str):
    """
    Chamado toda vez que chegar uma telemetria no MQTT.
    topic ex.: 'alissondev007/umidificador/31a7dbcc/telemetria'
    ou       'alissondev007/umidificador/telemetria' (3 potências)
    """
    try:
        dados = json.loads(payload)
    except json.JSONDecodeError:
        print("Payload de telemetria inválido:", payload)
        return

    db: Session = SessionLocal()
    try:
        # Descobrir baseTopic a partir do topic
        # Tomada: "base/telemetria" -> base = tudo antes de "/telemetria"
        if topic.endswith("/telemetria"):
            base_topic = topic.rsplit("/telemetria", 1)[0]
        else:
            # Se for um tópico fixo do 3P: você pode mapear direto por tipo
            base_topic = topic  # ajuste conforme sua necessidade

        dispositivo = encontrar_dispositivo_por_base_topic(db, base_topic)
        if not dispositivo:
            print("Nenhum dispositivo vinculado ao baseTopic:", base_topic)
            return

        leitura = Leitura(
            dispositivo_id=dispositivo.id,
            dados=dados,
        )
        db.add(leitura)
        db.commit()
    finally:
        db.close()
