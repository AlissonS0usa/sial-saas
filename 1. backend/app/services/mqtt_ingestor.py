import json
import threading
from typing import Optional

import paho.mqtt.client as mqtt
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.dispositivo import Dispositivo
from app.models.leitura import Leitura

# ---- Config vindo do settings ----
MQTT_BROKER_HOST = settings.MQTT_BROKER_HOST
MQTT_BROKER_PORT = settings.MQTT_BROKER_PORT
MQTT_TOPIC_ROOT = settings.MQTT_TOPIC_ROOT
MQTT_USERNAME = settings.MQTT_USERNAME
MQTT_PASSWORD = settings.MQTT_PASSWORD

_mqtt_client: Optional[mqtt.Client] = None


# ========= Helpers de banco =========

def get_db() -> Session:
    """
    Cria uma sessão nova de banco para uso dentro dos callbacks MQTT.
    """
    db = SessionLocal()
    return db


def find_dispositivo_by_base_topic(db: Session, base_topic: str) -> Optional[Dispositivo]:
    """
    Busca o dispositivo cujo config.mqtt.topic OU config.mqtt.baseTopic
    bate com base_topic.

    Espera no banco algo como:
      dispositivo.config = {
        "mqtt": {
          "topic": "alissondev007/umidificador/31a7dbcc"
        },
        ...
      }
    """
    cfg = Dispositivo.config  # JSONB

    return (
        db.query(Dispositivo)
        .filter(
            func.coalesce(
                cfg["mqtt"]["topic"].astext,
                cfg["mqtt"]["baseTopic"].astext
            ) == base_topic
        )
        .first()
    )


def salvar_leitura(db: Session, dispositivo: Dispositivo, dados: dict) -> None:
    leitura = Leitura(
        dispositivo_id=dispositivo.id,
        dados=dados,
    )
    db.add(leitura)
    db.commit()


# ========= Callbacks MQTT =========

def _on_connect(client: mqtt.Client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT-INGESTOR] Conectado ao broker.")
        topic = f"{MQTT_TOPIC_ROOT}/#"
        client.subscribe(topic)
        print(f"[MQTT-INGESTOR] Assinando: {topic}")
    else:
        print(f"[MQTT-INGESTOR] Falha na conexão. rc={rc}")


def _on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    topic = msg.topic
    payload_raw = msg.payload.decode(errors="ignore").strip()

    # Ex: alissondev007/umidificador/31a7dbcc/umidade
    partes = topic.split("/")
    if len(partes) < 3:
        return

    base_topic = "/".join(partes[:-1])
    sufixo = partes[-1]

    db = get_db()
    try:
        dispositivo = find_dispositivo_by_base_topic(db, base_topic)
        if not dispositivo:
            # Se quiser debugar:
            # print(f"[MQTT-INGESTOR] Nenhum dispositivo p/ base_topic={base_topic}")
            return

        dados: dict = {}

        if sufixo == "umidade":
            try:
                umid = float(payload_raw.replace(",", "."))
                dados["umidade"] = umid
            except ValueError:
                dados["umidade_raw"] = payload_raw

        elif sufixo == "status":
            dados["status"] = payload_raw

        elif sufixo == "potencia":
            try:
                pot = int(payload_raw)
                dados["potencia"] = pot
            except ValueError:
                dados["potencia_raw"] = payload_raw

        elif sufixo == "config-atual":
            try:
                cfg = json.loads(payload_raw)
                dados["config_atual"] = cfg
            except json.JSONDecodeError:
                dados["config_atual_raw"] = payload_raw

        else:
            # outros topics (ex: comando, config) não queremos registrar aqui
            return

        if not dados:
            return

        salvar_leitura(db, dispositivo, dados)

    except Exception as e:
        db.rollback()
        print(f"[MQTT-INGESTOR] Erro ao processar {topic}: {e}")
    finally:
        db.close()


# ========= Inicialização do ingestor =========

def start_mqtt_ingestor():
    """
    Cria o cliente MQTT, conecta ao broker e inicia o loop em uma thread daemon.
    Deve ser chamado no evento de startup do FastAPI.
    """
    global _mqtt_client
    if _mqtt_client is not None:
        # já foi inicializado
        return

    client = mqtt.Client(
        client_id="BACKEND-UMID-INGESTOR",
        clean_session=True,
    )

    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD or "")

    client.on_connect = _on_connect
    client.on_message = _on_message

    print(f"[MQTT-INGESTOR] Conectando em {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} ...")
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)

    thread = threading.Thread(target=client.loop_forever, daemon=True)
    thread.start()

    _mqtt_client = client
    print("[MQTT-INGESTOR] Ingestor MQTT iniciado em thread separada.")
