from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.db.session import SessionLocal
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut, UsuarioUpdate, UsuarioUpdateMe
from app.core.security import gerar_hash_senha
from app.core.deps import get_usuario_logado, get_db, requer_roles

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("/", response_model=UsuarioOut)
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=gerar_hash_senha(usuario.senha),
        role=usuario.role
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


@router.get("/me", response_model=UsuarioOut)
def usuario_logado(usuario: Usuario = Depends(get_usuario_logado)):
    return usuario

#listar todos os usuarios (apenas admin)
@router.get("/", dependencies=[Depends(requer_roles('ADMIN'))])
def listar_usuarios(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    ativo: Optional[bool] = Query(default=True, description="Filtrar por ativo/inativo"),
):
    q = db.query(Usuario)
    if ativo is not None:
        q = q.filter(Usuario.ativo == ativo)

    total = q.count()
    items = q.order_by(Usuario.criado_em.desc()).offset(offset).limit(limit).all()

    return {"items": items, "total": total, "limit": limit, "offset": offset}

#obter usuario especifica
@router.get("/{usuario_id}", response_model=UsuarioOut, dependencies=[Depends(requer_roles("ADMIN"))])
def obter_usuario(usuario_id: UUID, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.ativo == True).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario

@router.delete("/{usuario_id}")
def excluir_usuario(
    usuario_id: UUID,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado)
):
    # Permitir apenas admin excluir
    if usuario_logado.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem excluir usuários."
        )

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Impedir exclusão de si mesmo (opcional)
    if usuario.id == usuario_logado.id:
        raise HTTPException(
            status_code=400, detail="Você não pode excluir seu próprio usuário."
        )

    # Marca como inativo em vez de apagar
    usuario.ativo = False
    db.commit()

    return {"message": f"Usuário {usuario.nome} foi desativado com sucesso"}

@router.put("/{usuario_id}", response_model=UsuarioOut)
def atualizar_usuario(
    usuario_id: UUID,
    usuario_data: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado)
):
    # Somente admin pode editar outros usuários
    if usuario_logado.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem atualizar usuários."
        )

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Atualiza os campos informados
    for campo, valor in usuario_data.model_dump(exclude_unset=True).items():
        if campo == "senha":
            setattr(usuario, "senha_hash", gerar_hash_senha(valor))
        else:
            setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)
    return usuario

