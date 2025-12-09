# app/schemas/dashboard.py
from pydantic import BaseModel

class ResumoDashboard(BaseModel):
    clientes_ativos: int
    lugares_ativos: int
    dispositivos_online: int
    dispositivos_offline: int
