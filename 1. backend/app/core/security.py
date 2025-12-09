from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_senha(senha_plain, senha_hash):
    return pwd_context.verify(senha_plain, senha_hash)

def gerar_hash_senha(senha_plain):
    return pwd_context.hash(senha_plain)

def criar_token_acesso(sub: str, extra: Optional[dict] = None, expires_delta: Optional[timedelta] = None) -> str:
    """
    sub: ID do usuário (string)
    extra: quaisquer claims extras (ex.: {"role": "ADMIN"})
    """
    now = datetime.now(timezone.utc)
    exp = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": str(sub), "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decodificar_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
