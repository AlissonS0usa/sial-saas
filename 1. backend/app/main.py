from fastapi import FastAPI
from app.db.init_db import init_db  
from fastapi.middleware.cors import CORSMiddleware
from app.services.mqtt_ingestor import start_mqtt_ingestor
from app.api import auth, usuarios, dispositivos, leituras, lugares, dashboard, relatorios


app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # só permite esse origin
    allow_credentials=True,
    allow_methods=["*"],         # permite todos os métodos (GET, POST, etc)
    allow_headers=["*"],         # permite todos os headers
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(lugares.router)
app.include_router(dispositivos.router)
app.include_router(leituras.router)
app.include_router(dashboard.router)
app.include_router(relatorios.router)

@app.on_event("startup")
def on_startup():
    init_db()
    start_mqtt_ingestor()
