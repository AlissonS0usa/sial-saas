# app/routers/leituras.py
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_usuario_logado
from app.models.leitura import Leitura
from app.models.dispositivo import Dispositivo
from app.models.usuario import Usuario
from app.schemas.leitura import LeituraOut  # vamos criar já

router = APIRouter(prefix="/leituras", tags=["leituras"])


@router.get("/ultima/{dispositivo_id}", response_model=LeituraOut)
def obter_ultima_leitura(
    dispositivo_id: UUID,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    # Garante que o dispositivo é do usuário (ou ADMIN)
    q_disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id)
    if usuario.role != "ADMIN":
        q_disp = q_disp.filter(Dispositivo.lugar.has(usuario_id=usuario.id))

    dispositivo = q_disp.first()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado ou não pertence ao usuário.")

    leitura = (
        db.query(Leitura)
        .filter(Leitura.dispositivo_id == dispositivo_id)
        .order_by(Leitura.timestamp.desc())
        .first()
    )
    if not leitura:
        raise HTTPException(status_code=404, detail="Nenhuma leitura encontrada para este dispositivo.")

    return leitura


@router.get("/", response_model=List[LeituraOut])
def listar_leituras(
    dispositivo_id: UUID,
    inicio: Optional[datetime] = Query(None),
    fim: Optional[datetime]   = Query(None),
    limite: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_logado),
):
    q_disp = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id)
    if usuario.role != "ADMIN":
        q_disp = q_disp.filter(Dispositivo.lugar.has(usuario_id=usuario.id))

    dispositivo = q_disp.first()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado ou não pertence ao usuário.")

    q = db.query(Leitura).filter(Leitura.dispositivo_id == dispositivo_id)

    if inicio:
        q = q.filter(Leitura.timestamp >= inicio)
    if fim:
        q = q.filter(Leitura.timestamp <= fim)

    q = q.order_by(Leitura.timestamp.desc()).limit(limite)

    return q.all()
