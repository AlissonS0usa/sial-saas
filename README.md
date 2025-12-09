# Plataforma IoT de Monitoramento e Controle de Umidade

Este projeto é uma plataforma completa para **monitorar e controlar umidificadores** em ambientes fechados (como estufas, salas de cultivo, etc.), usando:

- **ESP32** + sensor de umidade/temperatura  
- **MQTT** para comunicação  
- **Backend** em FastAPI + PostgreSQL  
- **Frontend** em HTML/CSS/JavaScript  

A ideia é que qualquer pessoa com um pouco de conhecimento em programação consiga **rodar o sistema no computador** e, se quiser, depois **ligar um ESP32 de verdade** para controlar um umidificador.

> ⚠️ **Aviso sério de segurança:**  
> Se você for mexer com **tensão da tomada (110/220 V)**, relé, umidificador real etc., faça isso **só se souber o que está fazendo**. Errar aqui pode dar choque, curto, incêndio ou pior.  
> Se não tiver experiência, comece **apenas com o ESP32, LED e sensor**, nada ligado direto na rede elétrica.

---

## 1. Como o projeto é organizado

O projeto é dividido em três partes:

- `backend/` → API (FastAPI + PostgreSQL)  
- `frontend/` → Site (HTML + CSS + JavaScript puro)  
- `firmware/` → Códigos para ESP32 (umidificador, tomada inteligente etc.)

Estrutura geral:

```text
.
├─ backend/          # API FastAPI + PostgreSQL + JWT + SQLAlchemy
│  └─ README.md      # Explica em detalhe como rodar só o backend
│
├─ frontend/         # Interface Web (painéis de Admin e Cliente)
│  └─ README.md      # Explica em detalhe como rodar só o frontend
│
├─ firmware/         # Códigos para ESP32
│  ├─ dispositivo_umidificador/   # exemplo de código para controle de umidificador
│  └─ outros/                     # outros firmwares, se existirem
│
├─ docs/             # Documentação, requisitos, diagramas, etc.
│  ├─ Documento_Requisitos_Sistema.*
│  ├─ diagramas/
│  └─ outros_docs/
│
├─ .gitignore
└─ README.md         # (este arquivo)
```

### Em linguagem simples

- **Backend**: é o “cérebro” da aplicação. Guarda tudo no banco (usuários, dispositivos, leituras de umidade, etc.) e oferece uma API (endpoints) para o frontend e para outros serviços.
- **Frontend**: é o que você enxerga no navegador. Tela de login, dashboards, tabelas, gráficos, etc.
- **Firmware**: é o código que roda no ESP32 (microcontrolador). Ele lê o sensor, liga/desliga o umidificador e conversa com o resto do sistema via MQTT.

---

## 2. O que você precisa para testar em casa

### 2.1. Só no computador (sem hardware)

Se você quiser **apenas ver o sistema funcionando**, sem ESP32 de verdade:

- Git
- Python 3.11 ou superior
- PostgreSQL (pode ser local ou via Docker)
- (Opcional) Docker e Docker Compose
- Navegador (Chrome, Firefox, etc.)

### 2.2. Com ESP32 e umidificador de verdade

Além do que está acima, você vai precisar de:

- 1 × **ESP32** (devkit comum)
- 1 × **sensor de umidade/temperatura** (ex.: SHT30/SHT35 ou outro similar)
- 1 × **módulo de relé** ou **relé de estado sólido (SSR)** adequado para a carga do umidificador
- Fontes de alimentação devidamente dimensionadas
- Fios, protoboard, etc.

> ⚠️ De novo: **não ligue nada na tomada** se não entende bem de elétrica.  
> Dá pra testar muita coisa usando **só LED e baixa tensão**.

---

## 3. Passo a passo para rodar o projeto

### Passo 0 — Clonar o repositório

```bash
git clone https://github.com/SEU-USUARIO/NOME-DO-REPO.git
cd NOME-DO-REPO
```

---

### Passo 1 — Subir o banco de dados (PostgreSQL)

Você tem duas opções:

#### 1.1. Usar PostgreSQL instalado na máquina

1. Instale o PostgreSQL.
2. Crie um banco, por exemplo `umidificador`.
3. Anote:
   - usuário do banco (ex.: `postgres`)
   - senha (ex.: `minha_senha`)
   - host (`localhost`)
   - porta (`5432`)

Sua URL de conexão vai ficar parecida com:

```text
postgresql+psycopg2://postgres:minha_senha@localhost:5432/umidificador
```

#### 1.2. Usar PostgreSQL via Docker

Se preferir rodar o banco em um container:

```bash
docker run --name umidificador-db -e POSTGRES_DB=umidificador   -e POSTGRES_USER=usuario -e POSTGRES_PASSWORD=senha   -p 5432:5432 -d postgres:16
```

A URL de conexão fica algo como:

```text
postgresql+psycopg2://usuario:senha@localhost:5432/umidificador
```

---

### Passo 2 — Configurar o backend

Entre na pasta do backend:

```bash
cd backend
```

Crie um arquivo `.env` com as configurações mínimas:

```env
# Ambiente
ENVIRONMENT=dev
DEBUG=True

# Banco de Dados
DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/umidificador

# JWT (autenticação)
JWT_SECRET_KEY=uma_chave_bem_grande_e_secreta
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS (origens do frontend que podem chamar a API)
BACKEND_CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500

# MQTT (se quiser que o backend fale com o broker)
USE_MQTT=false
MQTT_BROKER_URL=broker.exemplo.com
MQTT_BROKER_PORT=1883
MQTT_USERNAME=usuario
MQTT_PASSWORD=senha
MQTT_CLIENT_ID=backend-umidificador
```

> ❗ Não suba esse `.env` pro Git (ele deve estar listado no `.gitignore`).

Crie e ative um ambiente virtual Python:

```bash
python -m venv .venv

# Windows
.venv\Scriptsctivate

# Linux/Mac
# source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Se o projeto usar migration (Alembic), aplique:

```bash
alembic upgrade head
```

Suba o backend:

```bash
uvicorn app.main:app --reload
```

A API vai rodar em:

- http://localhost:8000

Documentação automática (pra você explorar os endpoints):

- http://localhost:8000/docs  (Swagger UI)
- http://localhost:8000/redoc

> A partir do `/docs` você consegue testar as rotas: criar cliente, criar usuário admin, fazer login, etc.

---

### Passo 3 — Configurar o frontend

Abra outro terminal e vá para a pasta do frontend:

```bash
cd frontend
```

O frontend aqui é **estático** (HTML + CSS + JS).  
Você só precisa servir esses arquivos via HTTP.

#### 3.1. Ajustar o `config.js`

Procure o arquivo algo como `assets/js/config.js` e ajuste:

```javascript
export const USE_MQTT = false; // deixe false se não for usar ESP32 ainda

export const API_BASE_URL = "http://localhost:8000";

export const API_URLS = {
  login:        `${API_BASE_URL}/api/auth/login`,
  me:           `${API_BASE_URL}/api/auth/me`,
  clientes:     `${API_BASE_URL}/clientes`,
  lugares:      `${API_BASE_URL}/lugares`,
  dispositivos: `${API_BASE_URL}/dispositivos`,
  leituras:     `${API_BASE_URL}/leituras`,
  relatorios:   `${API_BASE_URL}/relatorios`, // se existir
};
```

#### 3.2. Servir o frontend

Opção simples com Python:

```bash
cd frontend
python -m http.server 5500
```

Acesse no navegador:

- http://localhost:5500/login.html  
  (ou a página inicial que estiver usando)

Ao tentar fazer login, o frontend vai chamar a API do backend em `http://localhost:8000`.

---

### Passo 4 — Criar usuário e testar login

1. Com o backend rodando, abra http://localhost:8000/docs
2. Procure as rotas de:
   - criação de **cliente** (`POST /clientes`)
   - criação de **usuário** (`POST /usuarios` ou similar)
3. Crie um usuário com papel `ADMIN` ou `CLIENTE` (isso depende do schema que o backend usa, veja no `/docs`).
4. Depois vá em `POST /api/auth/login`, informe email e senha desse usuário.
5. Confirme que a rota de login está funcionado: você deve receber um `access_token`.
6. Agora use o **frontend** (`login.html`), tente fazer login com as mesmas credenciais.

Se tudo estiver certo, você deve cair no dashboard (admin ou cliente, dependendo do perfil).

> Como cada pessoa pode adaptar o backend/rotas, olhe sempre o `/docs` da API para conferir exatamente quais endpoints existem e quais campos são obrigatórios.

---

## 4. E se eu quiser ligar um ESP32 de verdade?

Essa parte não é obrigatória para ver o projeto funcionando, mas é aqui que começa a parte “IoT de verdade”.

Resumo do que o ESP32 deve fazer:

1. Conectar no Wi-Fi.
2. Conectar no broker MQTT.
3. Ler o sensor de umidade/temperatura.
4. Publicar leituras em tópicos (exemplos):
   - `meusdispositivos/umidificador/{id}/umidade`
   - `meusdispositivos/umidificador/{id}/temperatura`
   - `meusdispositivos/umidificador/{id}/status`
5. Assinar um tópico de comando, por ex.:
   - `meusdispositivos/umidificador/{id}/comando`
6. Quando chegar um comando (por ex. `{"potencia": 2}`), o ESP32:
   - Atualiza o relé ou a saída correspondente;
   - Atualiza o status e, se quiser, publica de volta.

Dentro de `firmware/` você vai encontrar exemplos de código para ESP32.  
O fluxo geral para quem quer tentar em casa é:

1. Abrir o `.ino` no **Arduino IDE** ou usar **PlatformIO**.
2. Ajustar:
   - SSID e senha do seu Wi-Fi (ou usar WiFiManager, se o código suportar).
   - Endereço do broker MQTT (pode usar um público como HiveMQ para teste).
   - Tópicos MQTT (para bater com o que você vai usar no backend/frontend).
3. Fazer upload para o ESP32.
4. Abrir o Monitor Serial e ver se:
   - Conectou no Wi-Fi;
   - Conectou no broker MQTT;
   - Começou a publicar/assinar tópicos.

> A integração completa com o backend (salvar leituras no banco vindas do MQTT) depende de como você vai amarrar o broker com a API (direto no backend ou em outro serviço).  
> Para quem está começando, só ver o ESP32 publicando e o frontend mostrando dados já é um bom objetivo.

---

## 5. Fluxo resumido para quem quer “copiar e brincar”

1. **Clonar** o repo.
2. **Subir o PostgreSQL** (local ou Docker).
3. Configurar e rodar o **backend** (FastAPI).
4. Configurar e rodar o **frontend** (servidor estático).
5. Criar cliente e usuário via documentação `/docs` da API.
6. Logar pelo frontend e navegar nos dashboards.
7. (Opcional) Ligar um **ESP32** ao broker MQTT e, depois, integrar isso ao backend/frontend.

---

## 6. Riscos e limitações

- Mexer com **110/220 V** em casa **não é brinquedo**. Se você copiar o projeto,  
  comece **sem ligar nada na tomada**. Use só LED, relé em baixa tensão, etc.
- O projeto é um **exemplo educativo** e pode precisar de ajustes de segurança,  
  testes e robustez antes de virar produto real.
- A parte de MQTT pode exigir ajustes finos (tópicos, QoS, reconexão, etc.) dependendo do seu broker.

---

