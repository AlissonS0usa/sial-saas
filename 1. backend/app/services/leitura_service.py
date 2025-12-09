# app/services/leituras_service.py
import json
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.dispositivo import Dispositivo
from app.models.leitura import Leitura

# cache em memória dos últimos valores de cada dispositivo
_ultimo_estado: Dict[UUID, Dict[str, Any]] = {}


def _parse_topic(topic: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Entende de qual "base" é o tópico e qual métrica está vindo.
    Exemplos:
      - 'alissondev007/umidificador/31a7dbcc/umidade'
         -> base='alissondev007/umidificador/31a7dbcc', metric='umidade'
      - 'alissondev007/umidificador/umidade'
         -> base='alissondev007/umidificador', metric='umidade'
    """
    parts = topic.split("/")
    if len(parts) == 4 and parts[0] == "alissondev007" and parts[1] == "umidificador":
        base = "/".join(parts[:3])  # com deviceId
        metric = parts[3]
        return base, metric

    if len(parts) == 3 and parts[0] == "alissondev007" and parts[1] == "umidificador":
        base = "/".join(parts[:2])  # sem deviceId (3P)
        metric = parts[2]
        return base, metric

    return None, None


def _encontrar_dispositivo_por_base(db: Session, base_topic: str) -> Optional[Dispositivo]:
    """
    Para tomadas: usa config->mqtt->baseTopic.
    Para 3P: usa tipo 'umidificador_3p' e assume único.
    """
    if base_topic == "alissondev007/umidificador":
        # umidificador 3P (tópicos fixos)
        return (
            db.query(Dispositivo)
            .filter(Dispositivo.tipo == "umidificador_3p", Dispositivo.ativo == True)
            .first()
        )

    # Tomadas: base_topic inclui o deviceId
    # Necessário ter salvo em config.mqtt.baseTopic
    return (
        db.query(Dispositivo)
        .filter(
            Dispositivo.config["mqtt"]["baseTopic"].astext == base_topic,
            Dispositivo.ativo == True,
        )
        .first()
    )


def processar_mensagem_mqtt(topic: str, payload: str) -> None:
    base_topic, metric = _parse_topic(topic)
    if not base_topic or not metric:
        # tópico que não nos interessa
        return

    db: Session = SessionLocal()
    try:
        dispositivo = _encontrar_dispositivo_por_base(db, base_topic)
        if not dispositivo:
            print("Sem dispositivo vinculado a baseTopic:", base_topic)
            return

        # pega estado anterior (se tiver)
        estado = _ultimo_estado.get(dispositivo.id, {}).copy()

        if metric == "umidade":
            try:
                estado["umidade"] = float(payload)
            except ValueError:
                print("Umidade inválida:", payload)
                return

        elif metric == "status":
            # pode ser "Ligado"/"Desligado" ou "0"/"1"
            valor = payload.strip()
            if valor in ("0", "1"):
                estado["status"] = "ligado" if valor == "1" else "desligado"
            else:
                estado["status"] = valor  # já vem "Ligado", "Desligado" etc.

        elif metric == "potencia":
            try:
                estado["potencia"] = int(payload)
            except ValueError:
                print("Potência inválida:", payload)
                # não aborta: só não atualiza a potência

        else:
            # outros tópicos: ignora por enquanto
            return

        # Atualiza o cache
        _ultimo_estado[dispositivo.id] = estado

        # Salva leitura no banco
        leitura = Leitura(
            dispositivo_id=dispositivo.id,
            dados=estado,  # snapshot completo nesse momento
        )
        db.add(leitura)
        db.commit()

    finally:
        db.close()
