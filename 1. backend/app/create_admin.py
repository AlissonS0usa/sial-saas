import uuid
from app.db.session import SessionLocal
from app.models.usuario import Usuario
from app.core.security import gerar_hash_senha

db = SessionLocal()

db.query(Usuario).filter(Usuario.email == "admin@saas.com").delete()

admin = Usuario(
    id=uuid.uuid4(),
    nome="Administrador",
    email="admin@saas.com",
    senha_hash=gerar_hash_senha("admin123"),
    role="ADMIN",
    ativo=True,
)

db.add(admin)
db.commit()
db.refresh(admin)
print("✅ Usuário ADMIN criado com sucesso!")
print("E-mail:", admin.email)

