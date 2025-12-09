from app.db.base import Base  # que importa todos os models
from app.db.session import engine

def init_db():
    Base.metadata.create_all(bind=engine)
