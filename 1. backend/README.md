# Backend — Plataforma IoT de Monitoramento e Controle de Umidade

API REST desenvolvida com **FastAPI** para gerenciar usuários, clientes, lugares, dispositivos IoT e leituras de umidade/temperatura.  
Este backend faz parte de uma plataforma SaaS para controle de umidificadores conectados via **ESP32 + MQTT**.

---

## 📐 Visão Geral

### Objetivo do sistema

- Permitir que **administradores** cadastrem clientes, lugares e dispositivos IoT.
- Permitir que **clientes** visualizem e gerenciem seus próprios lugares e dispositivos.
- Registrar e consultar **leituras** enviadas pelos dispositivos (umidade, temperatura, status ligado/desligado).
- Disponibilizar endpoints seguros para:
  - **Autenticação** (login com JWT);
  - **Gestão de entidades principais** (clientes, lugares, dispositivos, usuários);
  - **Consulta de leituras** e geração de relatórios.

### Principais recursos

- Autenticação com **JWT** (login, obtenção de usuário logado, controle de acesso por perfil).
- Papel de usuário:
  - `ADMIN`: gerencia todo o sistema (clientes, lugares, dispositivos, usuários).
  - `CLIENTE`: gerencia apenas seus próprios lugares e dispositivos.
- CRUD de:
  - Usuários
  - Clientes
  - Lugares
  - Dispositivos
  - Leituras dos dispositivos
- Integração planejada com **MQTT** para:
  - Receber leituras em tempo real;
  - Atualizar status/potência do umidificador.

---

## 🛠️ Stack Tecnológica

- **Linguagem:** Python 3.11+
- **Framework Web:** FastAPI
- **Banco de Dados:** PostgreSQL (ex.: Neon, RDS, local, etc.)
- **ORM:** SQLAlchemy + Alembic (migrações)
- **Autenticação:** JWT (via `python-jose` ou similar)
- **Validação de dados:** Pydantic
- **Testes:** Pytest
- **Containerização:** Docker + Docker Compose (opcional)
- **Outros:**
  - Uvicorn (servidor ASGI)
  - python-dotenv (ou similar) para carregar `.env`

---

## 📁 Estrutura de Pastas (sugerida)

Ajuste conforme estiver o seu projeto, mas a ideia geral é:

```text
backend/
├─ app/
│  ├─ main.py               # Ponto de entrada da aplicação FastAPI
│  ├─ core/
│  │  ├─ config.py          # Configurações (leitura de .env)
│  │  ├─ security.py        # Funções JWT, autenticação, senhas
│  │  └─ deps.py            # Dependências comuns (ex.: get_db, get_current_user)
│  ├─ db/
│  │  ├─ base.py            # Base do SQLAlchemy
│  │  ├─ session.py         # SessionLocal, engine
│  │  └─ migrations/        # Alembic
│  ├─ models/               # Modelos SQLAlchemy (Usuario, Cliente, Lugar, Dispositivo, Leitura, etc.)
│  ├─ schemas/              # Schemas Pydantic (request/response)
│  ├─ api/
│  │  ├─ deps.py            # Dependências específicas das rotas
│  │  └─ v1/
│  │     ├─ api.py          # Include de todas as rotas v1
│  │     ├─ endpoints/
│  │     │  ├─ auth.py
│  │     │  ├─ usuarios.py
│  │     │  ├─ clientes.py
│  │     │  ├─ lugares.py
│  │     │  ├─ dispositivos.py
│  │     │  └─ leituras.py
│  ├─ services/             # Regras de negócio (opcional, mas recomendado)
│  └─ utils/                # Funções auxiliares
│
├─ tests/                   # Testes unitários/integrados
├─ requirements.txt         # Dependências do backend
├─ alembic.ini              # Configuração do Alembic
├─ Dockerfile               # Docker do backend
└─ README.md
