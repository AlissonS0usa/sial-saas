from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.security import decodificar_token
from app.db.session import SessionLocal
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_usuario_logado(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    payload = decodificar_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    usuario = db.query(Usuario).get(payload["sub"])
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario

def requer_roles(*roles: str):
    def _dep(usuario: Usuario = Depends(get_usuario_logado)) -> Usuario:
        role = getattr(usuario, "role", getattr(usuario, "tipo", None))
        if role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
        return usuario
    return _dep
