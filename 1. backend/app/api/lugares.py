from fastapi import APIRouter, Response, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from uuid import UUID
from typing import List

from app.db.session import SessionLocal
from app.models.lugar import Lugar
from app.schemas.lugar import LugarCreate, LugarUpdate, LugarOut, LugarBase
from app.models.usuario import Usuario
from app.models.dispositivo import Dispositivo
from app.core.deps import get_usuario_logado, get_db

router = APIRouter(prefix="/lugares", tags=["Lugares"])


# Criar novo lugar
@router.post("/", response_model=LugarOut)
def criar_lugar(
    lugar_in: LugarCreate,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado),
):
    # 1) Determina qual usuario_id vai ser usado
    if usuario_logado.role == "ADMIN":
        # Admin precisa informar explicitamente o cliente
        if not lugar_in.usuario_id:
            raise HTTPException(
                status_code=400,
                detail="Campo 'usuario_id' é obrigatório ao criar lugares como ADMIN.",
            )
        usuario_id = lugar_in.usuario_id
    else:
        # Cliente só pode criar lugar para ele mesmo
        usuario_id = usuario_logado.id

    # 2) (opcional) validar se o usuário existe/está ativo
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.ativo == True).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário vinculado ao lugar não encontrado ou inativo.")

    # 3) Criar o lugar
    novo = Lugar(
        nome=lugar_in.nome,
        cep=lugar_in.cep,
        rua=lugar_in.rua,
        numero=lugar_in.numero,
        bairro=lugar_in.bairro,
        cidade=lugar_in.cidade,
        estado=lugar_in.estado,
        complemento=lugar_in.complemento,
        usuario_id=usuario_id,
        ativo=True,
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


# Listar todos os lugares do usuário logado
@router.get("/", response_model=List[LugarOut])
def listar_lugares(
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado)
):
    query = db.query(Lugar).options(joinedload(Lugar.usuario)).filter(Lugar.ativo == True)

    # Se for cliente, mostra só os próprios
    if usuario_logado.role == "CLIENTE":
        query = query.filter(Lugar.usuario_id == usuario_logado.id)

    return query.all()


# Obter um lugar específico
@router.get("/{lugar_id}", response_model=LugarOut)
def obter_lugar(
    lugar_id: UUID,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado)
):
    query = db.query(Lugar).options(joinedload(Lugar.usuario))
    lugar = query.filter(Lugar.id == lugar_id, Lugar.ativo == True).first()

    if not lugar:
        raise HTTPException(status_code=404, detail="Lugar não encontrado")

    # 🔒 Se for cliente, garante que o lugar pertence a ele
    if usuario_logado.role != "ADMIN" and lugar.usuario_id != usuario_logado.id:
        raise HTTPException(status_code=403, detail="Sem permissão para acessar este lugar")

    return lugar


# 📌 Atualizar lugar existente
@router.put("/{lugar_id}", response_model=LugarOut)
def atualizar_lugar(
    lugar_id: UUID,
    lugar_data: LugarUpdate,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado)
):
    lugar = db.query(Lugar).filter(Lugar.id == lugar_id, Lugar.ativo == True).first()
    if not lugar:
        raise HTTPException(status_code=404, detail="Lugar não encontrado")

    # Apenas admin pode trocar o cliente vinculado
    if usuario_logado.role != "ADMIN" and lugar.usuario_id != usuario_logado.id:
        raise HTTPException(status_code=403, detail="Sem permissão para editar este lugar.")

    for campo, valor in lugar_data.model_dump(exclude_unset=True).items():
        setattr(lugar, campo, valor)

    db.commit()
    db.refresh(lugar)
    return lugar


# 📌 Excluir lugar
@router.delete("/{lugar_id}")
def excluir_lugar(
    lugar_id: UUID,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado),
):
    # Busca o lugar ativo
    q = db.query(Lugar).filter(Lugar.id == lugar_id, Lugar.ativo == True)

    # Cliente só vê o que é dele
    if usuario_logado.role != "ADMIN":
        q = q.filter(Lugar.usuario_id == usuario_logado.id)

    lugar = q.first()
    if not lugar:
        raise HTTPException(
            status_code=404,
            detail="Lugar não encontrado ou não pertence ao usuário.",
        )

    # bloquear exclusão se tiver dispositivos ativos no lugar
    dispositivos_ativos = (
        db.query(Dispositivo)
        .filter(Dispositivo.lugar_id == lugar.id, Dispositivo.ativo == True)
        .count()
    )
    if dispositivos_ativos > 0:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir um lugar com dispositivos ativos vinculados.",
        )

    # Exclusão lógica
    lugar.ativo = False
    db.commit()
    return Response(status_code=204)
