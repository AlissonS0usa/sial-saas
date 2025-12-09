from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel
import paho.mqtt.client as mqtt

from app.models.dispositivo import Dispositivo
from app.models.lugar import Lugar
from app.models.usuario import Usuario
from app.schemas.dispositivo import DispositivoCreate, DispositivoOut, DispositivoComandoIn, DispositivoUpdateLugar
from app.core.deps import get_usuario_logado, get_db

router = APIRouter(prefix="/dispositivos", tags=["dispositivos"])

MQTT_HOST = "broker.hivemq.com"
MQTT_PORT = 1883

mqtt_client = mqtt.Client()

def publish_mqtt(topic: str, payload: str, retain: bool = False):
    """
    Publica uma mensagem MQTT no broker configurado.
    Mantém um único client global bem simples.
    """
    if not mqtt_client.is_connected():
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt_client.publish(topic, payload, retain=retain)

def extrair_topic_comando(config: Dict[str, Any]) -> Optional[str]:
    """
    Tenta descobrir o tópico de comando a partir do JSON de config do dispositivo.
    Prioriza:
      1) config["mqtt"]["topics"]["comando"]
      2) config["mqtt"]["topicComando"] ou ["topic_comando"]
      3) config["mqtt"]["baseTopic"] + "/comando"
    """
    if not isinstance(config, dict):
        return None

    mqtt_cfg = config.get("mqtt")
    if not isinstance(mqtt_cfg, dict):
        return None

    # 1) topics.comando
    topics = mqtt_cfg.get("topics")
    if isinstance(topics, dict):
        topic_cmd = topics.get("comando")
        if isinstance(topic_cmd, str) and topic_cmd.strip():
            return topic_cmd.strip()

    # 2) topicComando / topic_comando
    for key in ("topicComando", "topic_comando"):
        val = mqtt_cfg.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # 3) baseTopic + "/comando"
    base = mqtt_cfg.get("baseTopic")
    if isinstance(base, str) and base.strip():
        return base.strip().rstrip("/") + "/comando"

    return None

def _extrair_umidades(config: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Tenta extrair umidadeMinima / umidadeMaxima do JSON de config.

    Procura nesses lugares, nessa ordem:
      1) config["umidadeMinima"] / config["umidadeMaxima"]
      2) config["controle"]["umidadeMinima"] / ["umidadeMaxima"]
      3) config["parametros"]["umidadeMinima"] / ["umidadeMaxima"]
    """
    umid_min = None
    umid_max = None

    # 1) raiz
    if "umidadeMinima" in config:
        umid_min = config["umidadeMinima"]
    if "umidadeMaxima" in config:
        umid_max = config["umidadeMaxima"]

    # 2) controle
    controle = config.get("controle")
    if isinstance(controle, dict):
        if umid_min is None and "umidadeMinima" in controle:
            umid_min = controle["umidadeMinima"]
        if umid_max is None and "umidadeMaxima" in controle:
            umid_max = controle["umidadeMaxima"]

    # 3) parametros
    parametros = config.get("parametros")
    if isinstance(parametros, dict):
        if umid_min is None and "umidadeMinima" in parametros:
            umid_min = parametros["umidadeMinima"]
        if umid_max is None and "umidadeMaxima" in parametros:
            umid_max = parametros["umidadeMaxima"]

    return umid_min, umid_max


def validar_config_por_tipo(tipo: str, config: Optional[Dict[str, Any]]) -> None:
    """
    Valida o JSON de config de acordo com o tipo do dispositivo.

    Para:
      - tomada_inteligente
      - umidificador_3p

    Garante que existam campos de umidade mínima/máxima em algum lugar do config,
    que sejam numéricos, 0–100, e que minima < maxima.
    """
    config = config or {}

    if tipo in ("tomada_inteligente", "umidificador_3p"):
        umid_min, umid_max = _extrair_umidades(config)

        if umid_min is None or umid_max is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Para dispositivos do tipo '{tipo}', "
                    "os campos 'umidadeMinima' e 'umidadeMaxima' são obrigatórios "
                    "no JSON de config (na raiz, em 'controle' ou em 'parametros')."
                ),
            )

        # Tipo
        if not isinstance(umid_min, (int, float)):
            raise HTTPException(
                status_code=400,
                detail="'umidadeMinima' deve ser numérico (int ou float).",
            )
        if not isinstance(umid_max, (int, float)):
            raise HTTPException(
                status_code=400,
                detail="'umidadeMaxima' deve ser numérico (int ou float).",
            )

        # Faixa
        if not 0 <= umid_min <= 100:
            raise HTTPException(
                status_code=400,
                detail="'umidadeMinima' deve estar entre 0 e 100.",
            )
        if not 0 <= umid_max <= 100:
            raise HTTPException(
                status_code=400,
                detail="'umidadeMaxima' deve estar entre 0 e 100.",
            )

        if umid_min >= umid_max:
            raise HTTPException(
                status_code=400,
                detail="'umidadeMinima' deve ser menor do que 'umidadeMaxima'.",
            )

        # (Se no futuro você quiser timers, dá pra validar aqui também)

    else:
        # Outros tipos ainda sem regra específica → não trava nada
        return


#Criar novo dispositivo vinculado a um lugar
@router.post("/", response_model=DispositivoOut)
def criar_dispositivo(
    dispositivo: DispositivoCreate,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado)
):
    # Admin pode criar para qualquer cliente/lugar ativo
    if usuario_logado.role == "ADMIN":
        lugar = db.query(Lugar).filter(
            Lugar.id == dispositivo.lugar_id,
            Lugar.ativo == True
        ).first()
        if not lugar:
            raise HTTPException(status_code=404, detail="Lugar não encontrado ou inativo")
    else:
        #Clientes só podem criar para seus próprios lugares
        lugar = db.query(Lugar).filter(
            Lugar.id == dispositivo.lugar_id,
            Lugar.usuario_id == usuario_logado.id,
            Lugar.ativo == True
        ).first()
        if not lugar:
            raise HTTPException(status_code=403, detail="Lugar inválido ou não pertence ao usuário")

    #Validações específicas por tipo (opcional)
    #validar_config_por_tipo(dispositivo.tipo, dispositivo.config)

    novo = Dispositivo(
        nome=dispositivo.nome,
        localizacao=dispositivo.localizacao,
        lugar_id=dispositivo.lugar_id,
        tipo=dispositivo.tipo,
        status=dispositivo.status,
        config=dispositivo.config,
        ativo=True,
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo



@router.get("/", response_model=List[DispositivoOut])
def listar_dispositivos(
    lugar_id: Optional[UUID] = Query(None, description="Filtra por lugar (opcional)"),
    tipo: Optional[str] = Query(None, description="Filtra por tipo (opcional)"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    q = (
        db.query(Dispositivo)
        .join(Dispositivo.lugar)  # 👈 FAZ O JOIN COM LUGAR
        .options(
            joinedload(Dispositivo.lugar).joinedload(Lugar.usuario)
        )
        .filter(Dispositivo.ativo == True)
    )

    # Cliente só enxerga dispositivos dos lugares dele
    if usuario.role != "ADMIN":
        q = q.filter(Lugar.usuario_id == usuario.id)

    if lugar_id:
        q = q.filter(Dispositivo.lugar_id == lugar_id)

    if tipo:
        q = q.filter(Dispositivo.tipo == tipo)

    return q.all()



@router.get("/{dispositivo_id}", response_model=DispositivoOut)
def obter_dispositivo(
    dispositivo_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    q = (
        db.query(Dispositivo)
        .join(Dispositivo.lugar)
        .options(
            joinedload(Dispositivo.lugar).joinedload(Lugar.usuario)
        )
        .filter(
            Dispositivo.id == dispositivo_id,
            Dispositivo.ativo == True,
        )
    )

    if usuario.role != "ADMIN":
        q = q.filter(Lugar.usuario_id == usuario.id)

    dispositivo = q.first()

    if not dispositivo:
        raise HTTPException(
            status_code=404,
            detail="Dispositivo não encontrado ou não pertence ao usuário",
        )

    return dispositivo





@router.put("/{dispositivo_id}", response_model=DispositivoOut)
def atualizar_dispositivo(
    dispositivo_id: UUID,
    dispositivo_in: DispositivoCreate,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado)
):
    q = db.query(Dispositivo).join(Dispositivo.lugar).options(
        joinedload(Dispositivo.lugar).joinedload(Lugar.usuario)
    ).filter(
        Dispositivo.id == dispositivo_id,
        Dispositivo.ativo == True
    )

    if usuario_logado.role != "ADMIN":
        q = q.filter(Lugar.usuario_id == usuario_logado.id)

    dispositivo = q.first()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado ou não pertence ao usuário")

    # Validação por tipo novamente (caso mude config/tipo)
    #validar_config_por_tipo(dispositivo_in.tipo, dispositivo_in.config)

    # Atualiza campos principais
    dispositivo.nome = dispositivo_in.nome
    dispositivo.localizacao = dispositivo_in.localizacao
    dispositivo.lugar_id = dispositivo_in.lugar_id
    dispositivo.tipo = dispositivo_in.tipo
    dispositivo.status = dispositivo_in.status
    dispositivo.config = dispositivo_in.config

    db.commit()
    db.refresh(dispositivo)
    return dispositivo





@router.post("/{dispositivo_id}/comando")
def enviar_comando_dispositivo(
    dispositivo_id: UUID,
    comando: DispositivoComandoIn,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    """
    Recebe uma ação de comando vinda do frontend e repassa para o dispositivo via MQTT.

    Ação esperada (comando.acao):
      - Para tomada_inteligente:
          "ativar", "ligar", "desligar"
      - Para umidificador_3p:
          "ativar", "desligar",
          "potencia1", "potencia2", "potencia3"
    """

    # 1) Busca dispositivo com filtro de permissão igual ao obter_dispositivo
    q = (
        db.query(Dispositivo)
        .join(Dispositivo.lugar)
        .options(joinedload(Dispositivo.lugar).joinedload(Lugar.usuario))
        .filter(
            Dispositivo.id == dispositivo_id,
            Dispositivo.ativo == True,
        )
    )

    if usuario.role != "ADMIN":
        q = q.filter(Lugar.usuario_id == usuario.id)

    dispositivo = q.first()
    if not dispositivo:
        raise HTTPException(
            status_code=404,
            detail="Dispositivo não encontrado ou não pertence ao usuário",
        )

    # 2) Descobre tópico de comando a partir do config
    cfg = dispositivo.config or {}
    tipo = (dispositivo.tipo or "").strip()
    acao_norm = comando.acao.strip().lower()

    # Descobre o tópico de comando
    topic_cmd: Optional[str] = None

    if tipo == "umidificador_3p":
        # 1) tenta pegar do config
        topic_cmd = extrair_topic_comando(cfg)
        # 2) se não tiver nada configurado, usa o tópico fixo
        if not topic_cmd:
            topic_cmd = "alissondev007/umidificador/comando"

    elif tipo == "tomada_inteligente":
        # Para a tomada, cada dispositivo tem seu baseTopic próprio,
        # então aqui a config PRECISA ter isso preenchido
        topic_cmd = extrair_topic_comando(cfg)
        if not topic_cmd:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Config MQTT do dispositivo não possui tópico de comando. "
                    "Para 'tomada_inteligente', preencha config.mqtt.baseTopic "
                    "ou config.mqtt.topics.comando."
                ),
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de dispositivo '{tipo}' não suporta envio de comandos via API.",
        )

    tipo = (dispositivo.tipo or "").strip()
    acao_norm = comando.acao.strip().lower()

    # 3) Mapeia acao -> payload MQTT de acordo com o firmware
    payload: str

    if tipo == "tomada_inteligente":
        # Firmware da tomada inteligente espera:
        #   "LIGAR" / "DESLIGAR" no tópico /comando
        if acao_norm in ("ativar", "ligar", "on"):
            payload = "LIGAR"
        elif acao_norm in ("desativar", "desligar", "off"):
            payload = "DESLIGAR"
        else:
            raise HTTPException(
                status_code=400,
                detail="Ação inválida para tomada_inteligente. Use 'ativar', 'ligar' ou 'desligar'.",
            )

    elif tipo == "umidificador_3p":
        # Firmware de 3 potências espera:
        #   "ativar", "desligar", "potencia1", "potencia2", "potencia3"
        if acao_norm in ("ativar", "desligar", "potencia1", "potencia2", "potencia3"):
            payload = acao_norm
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Ação inválida para umidificador_3p. "
                    "Use 'ativar', 'desligar', 'potencia1', 'potencia2' ou 'potencia3'."
                ),
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de dispositivo '{tipo}' não suporta envio de comandos via API.",
        )

    # 4) Publica no MQTT
    try:
        publish_mqtt(topic_cmd, payload, retain=False)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao publicar comando no MQTT: {e}",
        )

    return {
        "ok": True,
        "dispositivo_id": dispositivo_id,
        "tipo": tipo,
        "acao_recebida": comando.acao,
        "payload_enviado": payload,
        "topic": topic_cmd,
    }

@router.put("/{dispositivo_id}/mudar-lugar", response_model=DispositivoOut)
def mudar_dispositivo_de_lugar(
    dispositivo_id: UUID,
    body: DispositivoUpdateLugar,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado),
):
    # 1) Garante que o dispositivo existe e pertence ao usuário (se não for ADMIN)
    q = (
        db.query(Dispositivo)
        .join(Dispositivo.lugar)
        .filter(Dispositivo.id == dispositivo_id, Dispositivo.ativo == True)
    )

    if usuario_logado.role != "ADMIN":
        q = q.filter(Lugar.usuario_id == usuario_logado.id)

    dispositivo = q.first()
    if not dispositivo:
        raise HTTPException(
            status_code=404,
            detail="Dispositivo não encontrado ou não pertence ao usuário",
        )

    # 2) Valida o lugar de destino
    q_lugar = db.query(Lugar).filter(
        Lugar.id == body.lugar_id,
        Lugar.ativo == True,
    )

    if usuario_logado.role != "ADMIN":
        q_lugar = q_lugar.filter(Lugar.usuario_id == usuario_logado.id)

    lugar_dest = q_lugar.first()
    if not lugar_dest:
        raise HTTPException(
            status_code=403,
            detail="Lugar de destino inválido ou não pertence ao usuário.",
        )

    # 3) Atualiza o lugar
    dispositivo.lugar_id = lugar_dest.id

    db.add(dispositivo)
    db.commit()
    db.refresh(dispositivo)

    return dispositivo

@router.delete("/{dispositivo_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_dispositivo(
    dispositivo_id: UUID,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado),
):
    """
    Exclui (ou desativa) um dispositivo.

    - ADMIN pode excluir qualquer dispositivo ativo.
    - Cliente só pode excluir dispositivos de lugares dele.
    - Aqui fazemos soft delete (ativo = False) para não perder histórico de leituras.
    """

    # Busca dispositivo com o mesmo padrão de permissão das outras rotas
    q = (
        db.query(Dispositivo)
        .join(Dispositivo.lugar)
        .filter(
            Dispositivo.id == dispositivo_id,
            Dispositivo.ativo == True,
        )
    )

    if usuario_logado.role != "ADMIN":
        q = q.filter(Lugar.usuario_id == usuario_logado.id)

    dispositivo = q.first()
    if not dispositivo:
        raise HTTPException(
            status_code=404,
            detail="Dispositivo não encontrado ou não pertence ao usuário",
        )

    # Soft delete
    if hasattr(dispositivo, "ativo"):
        dispositivo.ativo = False
        db.add(dispositivo)
    else:
        # Se por algum motivo não tiver campo ativo, faz delete físico
        db.delete(dispositivo)

    db.commit()

