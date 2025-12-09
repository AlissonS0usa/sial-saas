from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_usuario_logado
from app.core.security import verificar_senha, criar_token_acesso, gerar_hash_senha
from app.models.usuario import Usuario
from app.schemas.token import Token
from app.schemas.usuario import UsuarioOut, UsuarioUpdateMe, AlterarSenhaRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # username=email (padrão OAuth2)
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if getattr(usuario, "ativo", True) is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo")

    # role no token (opcional, útil em clients)
    token = criar_token_acesso(sub=str(usuario.id), extra={"role": getattr(usuario, "role", None)})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_usuario_logado)):
    return usuario

@router.put("/me", response_model=UsuarioOut)
def atualizar_me(
    dados: UsuarioUpdateMe,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado),
):
    """
    Atualiza dados básicos do usuário logado (nome e, opcionalmente, e-mail).
    """
    alterou_algo = False

    # Nome
    if dados.nome is not None and dados.nome.strip() and dados.nome != usuario_logado.nome:
        usuario_logado.nome = dados.nome.strip()
        alterou_algo = True

    # E-mail (opcionalmente)
    if dados.email is not None and dados.email != usuario_logado.email:
        # Verifica se já existe outro usuário com esse e-mail
        existe = (
            db.query(Usuario)
            .filter(Usuario.email == dados.email, Usuario.id != usuario_logado.id)
            .first()
        )
        if existe:
            raise HTTPException(status_code=400, detail="Já existe um usuário com esse e-mail.")
        usuario_logado.email = dados.email
        alterou_algo = True

    if not alterou_algo:
        # Nada mudou, só retorna o próprio usuário
        return usuario_logado

    db.add(usuario_logado)
    db.commit()
    db.refresh(usuario_logado)
    return usuario_logado

@router.post("/alterar-senha")
def alterar_senha(
    body: AlterarSenhaRequest,
    db: Session = Depends(get_db),
    usuario_logado: Usuario = Depends(get_usuario_logado),
):
    """
    Altera a senha do usuário logado.
    - Confere a senha atual
    - Gera hash da nova senha
    """
    # 1) Verifica senha atual
    if not verificar_senha(body.senha_atual, usuario_logado.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    # 2) validar política de senha
    if len(body.nova_senha) < 8:
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve ter pelo menos 8 caracteres.",
        )

    if body.nova_senha == body.senha_atual:
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve ser diferente da senha atual.",
        )

    # 3) Atualiza hash
    usuario_logado.senha_hash = gerar_hash_senha(body.nova_senha)

    db.add(usuario_logado)
    db.commit()

    return {"detail": "Senha alterada com sucesso."}

