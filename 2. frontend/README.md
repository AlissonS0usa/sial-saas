# Frontend — Plataforma IoT de Monitoramento e Controle de Umidade

Interface web da plataforma SaaS para gestão de **clientes, lugares e dispositivos IoT** (umidificadores, tomadas inteligentes, etc.).  
Desenvolvida em **HTML + CSS + JavaScript puro**, consumindo a API do backend (FastAPI) e, opcionalmente, integrando com MQTT via WebSocket.

---

## 🎯 Objetivo do Frontend

- Permitir que **usuários Admin**:
  - Façam login.
  - Visualizem um dashboard com visão geral (clientes, lugares, dispositivos).
  - Gerenciem clientes, lugares e dispositivos.
  - Acessem relatórios e leituras dos dispositivos.

- Permitir que **clientes**:
  - Façam login.
  - Visualizem apenas seus próprios lugares e dispositivos.
  - Acessem detalhes de cada dispositivo (umidade, temperatura, status).
  - Controlem a potência do umidificador (quando aplicável).

---

## 🛠️ Stack Utilizada

- **HTML5** — Estrutura das páginas (divididas em telas de login, admin, cliente, etc.).
- **CSS3** — Estilização responsiva, seguindo um padrão visual único (cores, cards, tabelas, menus).
- **JavaScript (ES6+)** — Lógica de:
  - Login e armazenamento de token JWT.
  - Chamada da API do backend (Fetch API).
  - Atualização dinâmica de dashboards e tabelas.
  - Integração opcional com MQTT (via MQTT.js em WebSocket).
- **Bibliotecas externas (via CDN):**
  - [Chart.js](https://www.chartjs.org/) — gráficos no dashboard (leituras, dispositivos, etc.).
  - [MQTT.js](https://github.com/mqttjs/MQTT.js) — conexão WebSocket com o broker MQTT (quando ativado).
  - Outros (se utilizados): ícones, fontes, etc.

> Não há build step (sem bundler). É um frontend estático servido diretamente pelo navegador ou por um servidor HTTP simples.

---

## 📂 Estrutura de Pastas (sugerida)

Ajuste para refletir exatamente o que você tem hoje, mas a ideia geral é:

```text
frontend/
├─ index.html                  # (opcional) redireciona para login ou página inicial
├─ login.html                  # tela de login
│
├─ admin/
│  ├─ dashboard_admin.html     # dashboard do administrador
│  ├─ clientes.html            # gestão de clientes
│  ├─ lugares.html             # gestão de lugares
│  ├─ dispositivos.html        # gestão de dispositivos
│  ├─ relatorios.html          # relatórios e filtros
│  └─ ...                      # outras telas específicas de admin
│
├─ cliente/
│  ├─ dashboard_cliente.html   # dashboard do cliente
│  ├─ meus_dispositivos.html   # listagem de dispositivos do cliente
│  ├─ dispositivo.html         # tela de dispositivo específico (detalhes, umidade, potência, etc.)
│  └─ ...                      # outras telas específicas de cliente
│
├─ assets/
│  ├─ css/
│  │  ├─ base.css              # estilos globais (fonts, cores, layout base)
│  │  ├─ layout.css            # cabeçalho, menus, cards, grid
│  │  ├─ forms.css             # formulários, inputs, botões
│  │  ├─ tabelas.css           # tabelas (responsivas, scroll em mobile, etc.)
│  │  └─ pages/                # estilos específicos por página (opcional)
│  │
│  ├─ js/
│  │  ├─ config.js             # configuração da API e do MQTT
│  │  ├─ auth.js               # login, logout, verificação de token
│  │  ├─ api.js                # funções genéricas de chamada à API (GET, POST, PUT, DELETE)
│  │  ├─ ui.js                 # funções auxiliares de UI (mensagens, loaders, etc.)
│  │  ├─ admin/
│  │  │  ├─ dashboard_admin.js
│  │  │  ├─ clientes.js
│  │  │  ├─ lugares.js
│  │  │  ├─ dispositivos.js
│  │  │  └─ relatorios.js
│  │  ├─ cliente/
│  │  │  ├─ dashboard_cliente.js
│  │  │  ├─ meus_dispositivos.js
│  │  │  └─ dispositivo.js
│  │  └─ mqtt/
│  │     └─ mqtt_client.js     # conexão e callbacks MQTT (se usado no frontend)
│  │
│  └─ img/
│     ├─ logo.png
│     ├─ icones/
│     └─ ...
│
└─ README.md
