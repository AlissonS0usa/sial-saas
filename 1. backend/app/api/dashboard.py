
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.deps import get_db, get_usuario_logado
from app.models.usuario import Usuario
from app.models.lugar import Lugar
from app.models.dispositivo import Dispositivo
from app.schemas.dashboard import ResumoDashboard

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/resumo", response_model=ResumoDashboard)
def obter_resumo_dashboard(
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado)
):
    """
    Retorna os contadores do dashboard.
    - ADMIN: visão geral do sistema
    - CLIENTE: apenas dados do próprio tenant/usuário
    """

    is_admin = (usuario_logado.role or "").upper() == "ADMIN"

    # Base queries
    q_usuarios  = db.query(func.count(Usuario.id)).filter(Usuario.ativo == True)
    q_lugares   = db.query(func.count(Lugar.id)).filter(Lugar.ativo == True)
    q_disp_on   = db.query(func.count(Dispositivo.id)).filter(Dispositivo.ativo == True, Dispositivo.status == "online")
    q_disp_off  = db.query(func.count(Dispositivo.id)).filter(Dispositivo.ativo == True, Dispositivo.status != "online")

    if not is_admin:
        # Escopo por cliente (usuario_logado)
        q_lugares   = q_lugares.filter(Lugar.usuario_id == usuario_logado.id)
        q_disp_on   = q_disp_on.join(Lugar, Lugar.id == Dispositivo.lugar_id).filter(Lugar.usuario_id == usuario_logado.id)
        q_disp_off  = q_disp_off.join(Lugar, Lugar.id == Dispositivo.lugar_id).filter(Lugar.usuario_id == usuario_logado.id)

        # Para clientes, "clientes ativos" = 1 (ele mesmo) se ativo; senão 0
        clientes_ativos = 1 if usuario_logado.ativo else 0
    else:
        # Para admin, conta apenas usuários com role CLIENTE (case-insensitive)
        clientes_ativos = db.query(func.count(Usuario.id)).filter(
            Usuario.ativo == True,
            func.lower(Usuario.role) == "cliente"
        ).scalar()

    lugares_ativos      = q_lugares.scalar()
    dispositivos_online = q_disp_on.scalar()
    dispositivos_offline= q_disp_off.scalar()

    return ResumoDashboard(
        clientes_ativos=clientes_ativos or 0,
        lugares_ativos=lugares_ativos or 0,
        dispositivos_online=dispositivos_online or 0,
        dispositivos_offline=dispositivos_offline or 0
    )
