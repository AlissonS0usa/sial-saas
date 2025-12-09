/***********************
 * ESP32 + SHT30 (I2C) + LCD + WiFiManager + MQTT
 * Controle de TOMADA via 1 relé (ativo em HIGH)
 ***********************/

#include <WiFi.h>
#include <WiFiManager.h>
#include <PubSubClient.h>
#include <Adafruit_SHT31.h>
#include <LiquidCrystal_I2C.h>
#include <cstring>
#include <Preferences.h>

#define RELE_PIN 2
#define TEMPO_BOOT_SEGURO_MS 0

// LCD
int lcdColumns = 16, lcdRows = 2;
LiquidCrystal_I2C lcd(0x27, lcdColumns, lcdRows);

// Sensor
Adafruit_SHT31 sht30 = Adafruit_SHT31();

// Controle
int statusUmid = 0;
int umidadeMinima = 50;
int umidadeMaxima = 60;
bool sistemaAtivo = true;

Preferences prefs;

// MQTT
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

const char* MQTT_HOST = "broker.hivemq.com";
const uint16_t MQTT_PORT = 1883;

String deviceId;
String baseTopic, topicUmidade, topicStatus, topicConfigAtual, topicComando, topicConfig, topicConn;

// Timers
unsigned long lastSensorMs = 0;
const unsigned long INTERVALO_SENSOR_MS = 5000;

// ==================== PROTEÇÕES / ROBUSTEZ ====================

// Fail-safe de leitura (NaN / falhas seguidas)
int falhasSeguidas = 0;
const int FALHAS_MAX = 3;   // após 3 leituras ruins, força OFF

// Anti-condensação (heater)
const float LIMITE_UMID_HEATER = 95.0;           // acima disso pode acionar heater
const unsigned long HEATER_INTERVAL_MS = 60000;  // no máximo 1 vez por minuto
unsigned long ultimoHeaterMs = 0;

// Proteção 1: tempo máximo ligado sem atingir o limite
unsigned long momentoLigouUmidificador = 0;
const unsigned long TEMPO_MAX_LIGADO_MS = 20UL * 60UL * 1000UL; // 20 minutos

// Proteção 2: muito tempo com umidade >= 98%
bool contandoAcima98 = false;
unsigned long momentoAcima98 = 0;
const unsigned long TEMPO_MAX_UMID_ALTA_MS = 10UL * 60UL * 1000UL; // 10 minutos

// Wi-Fi / MQTT estado
bool wifiConectado = false;
bool mqttHabilitado = true;   // se falhar 5x, desabilita novas tentativas

// ===============================================================

// --- LCD ---
void lcdSplash(const char* l1, const char* l2 = "", uint16_t holdMs = 700) {
  lcd.clear();
  if (l1 && *l1) { lcd.setCursor((16 - (int)strlen(l1))/2, 0); lcd.print(l1); }
  if (l2 && *l2) { lcd.setCursor((16 - (int)strlen(l2))/2, 1); lcd.print(l2); }
  delay(holdMs);
}

void mostrarUmidadeStatus(float umidade, int status) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Umidade: ");
  if (!isnan(umidade)) { lcd.print(umidade, 0); lcd.print(" %"); }
  else { lcd.print("--"); }
  lcd.setCursor(0, 1);
  lcd.print("Status: ");
  lcd.print(status ? "Ligado" : "Deslig.");
}

// --- Relé ---
void aplicarSaidaRele(int novoStatus) {
  if (novoStatus == 1) {
    digitalWrite(RELE_PIN, HIGH);  // liga o relé
    Serial.print("Rele: Ligado");
  } else {
    digitalWrite(RELE_PIN, LOW);   // desliga o relé
    Serial.print("Rele: Desligado");
  }
}

// --- Anti-condensação / heater ---
void usarHeaterSePrecisar(float umidade) {
  unsigned long agora = millis();

  // só considera heater se estiver MUITO úmido
  if (umidade < LIMITE_UMID_HEATER) return;

  // limita frequência de uso
  if (agora - ultimoHeaterMs < HEATER_INTERVAL_MS) return;

  ultimoHeaterMs = agora;
  Serial.println("Heater SHT30: ativando para secar sensor...");

  sht30.heater(true);
  delay(800);                  // aquece ~0,8 s
  (void)sht30.readHumidity();  // descarta 1 leitura
  sht30.heater(false);
  delay(50);
}

// --- Publicações MQTT ---
void publicarConfigAtual(bool retain = true) {
  String json = String("{\"umidadeMinima\":") + umidadeMinima +
                ",\"umidadeMaxima\":" + umidadeMaxima + "}";
  mqttClient.publish(topicConfigAtual.c_str(), json.c_str(), retain);
  Serial.print("Publicou config atual: ");
  Serial.println(json);
}

void publicarStatusRetido() {
  mqttClient.publish(topicStatus.c_str(), String(statusUmid).c_str(), true);
  Serial.print("Publicou status: ");
  Serial.println(statusUmid ? "Ligado" : "Desligado");
}

void publicarUmidade(float umid) {
  char buf[16]; dtostrf(umid, 0, 1, buf);
  mqttClient.publish(topicUmidade.c_str(), buf, false);
  Serial.print("Publicou umidade: ");
  Serial.println(buf);
}

// --- NVS ---
void carregarLimitesNVS() {
  Serial.println("Carregando limites da NVS...");
  if (prefs.begin("umid_cfg", true)) {
    umidadeMinima = prefs.getInt("uMin", umidadeMinima);
    umidadeMaxima = prefs.getInt("uMax", umidadeMaxima);
    prefs.end();
  }
  Serial.printf("Limites carregados: Min=%d Max=%d\n", umidadeMinima, umidadeMaxima);
}

void salvarLimitesNVS() {
  Serial.println("Salvando limites na NVS...");
  if (prefs.begin("umid_cfg", false)) {
    prefs.putInt("uMin", umidadeMinima);
    prefs.putInt("uMax", umidadeMaxima);
    prefs.end();
  }
  Serial.printf("Limites salvos: Min=%d Max=%d\n", umidadeMinima, umidadeMaxima);
}

// --- MQTT callback ---
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String top = String(topic);
  String msg; msg.reserve(length+1);
  for (unsigned int i=0; i<length; i++) msg += (char)payload[i];
  Serial.printf("Mensagem MQTT recebida [%s]: %s\n", topic, msg.c_str());

  if (top == topicComando) {
    if (msg.equalsIgnoreCase("LIGAR")) {
      sistemaAtivo = true;
      Serial.println("Comando: LIGAR sistema");
    } else if (msg.equalsIgnoreCase("DESLIGAR")) {
      sistemaAtivo = false;
      statusUmid = 0;
      aplicarSaidaRele(statusUmid);
      publicarStatusRetido();
      Serial.println("Comando: DESLIGAR sistema");
    }
  }
  else if (top == topicConfig) {
    int idxMin = msg.indexOf("\"umidadeMinima\"");
    int idxMax = msg.indexOf("\"umidadeMaxima\"");
    if (idxMin >= 0) {
      int c = msg.indexOf(':', idxMin); int e = msg.indexOf(',', c); if (e<0) e = msg.indexOf('}', c);
      if (c>0 && e>c) umidadeMinima = msg.substring(c+1, e).toInt();
    }
    if (idxMax >= 0) {
      int c = msg.indexOf(':', idxMax); int e = msg.indexOf(',', c); if (e<0) e = msg.indexOf('}', c);
      if (c>0 && e>c) umidadeMaxima = msg.substring(c+1, e).toInt();
    }
    salvarLimitesNVS();
    publicarConfigAtual(true);
  }
}

// --- WiFi e MQTT ---
void conectaWiFiComWiFiManager() {
  Serial.println("Conectando WiFi...");
  WiFi.mode(WIFI_STA);
  WiFiManager wm;

  // dá 2 minutos para o usuário conectar no portal
  wm.setConfigPortalTimeout(120);  // 120 segundos
  // opcional: tempo máximo tentando conectar numa rede já salva
  wm.setConnectTimeout(30);

  bool ok = wm.autoConnect("UMID-Setup");
  if (!ok) {
    Serial.println("WiFiManager: não conectou em 2 minutos. Seguindo em modo OFFLINE (sem WiFi/MQTT).");
    wifiConectado = false;
    return;
  }

  wifiConectado = true;
  Serial.print("WiFi conectado! IP: ");
  Serial.println(WiFi.localIP());
}

void reconnectMQTT() {
  if (!wifiConectado) {
    // sem Wi-Fi, não faz sentido tentar MQTT
    return;
  }
  if (!mqttHabilitado) {
    // já falhou demais, não tenta mais
    return;
  }

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);

  int tentativas = 0;
  while (!mqttClient.connected() && tentativas < 5) {
    String clientId = "ESP32-UMID-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.print("Conectando MQTT como ");
    Serial.println(clientId);

    bool ok = mqttClient.connect(clientId.c_str());
    if (ok) {
      Serial.println("MQTT conectado!");
      mqttClient.subscribe(topicComando.c_str());
      mqttClient.subscribe(topicConfig.c_str());
      publicarStatusRetido();
      publicarConfigAtual(true);
      mqttClient.publish(topicConn.c_str(), "ONLINE", true);
      return; // conectado com sucesso
    } else {
      Serial.print("Falha MQTT, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" Tentando novamente em 1.5s...");
      tentativas++;
      delay(1500);
    }
  }

  if (!mqttClient.connected()) {
    Serial.println("Falha MQTT após 5 tentativas. Seguindo SEM MQTT (controle local apenas).");
    mqttHabilitado = false;
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(RELE_PIN, OUTPUT);
  digitalWrite(RELE_PIN, LOW);

  lcd.init(); lcd.backlight();
  lcdSplash("Inicializando");

  if (!sht30.begin(0x44)) {
    Serial.println("Erro: SHT30 não encontrado!");
    lcdSplash("Erro", "SHT30");
    while (1) delay(10);
  }

  deviceId = "31a7dbcc";
  baseTopic = String("alissondev007/umidificador/") + deviceId;
  topicUmidade     = baseTopic + "/umidade";
  topicStatus      = baseTopic + "/status";
  topicConfigAtual = baseTopic + "/config-atual";
  topicComando     = baseTopic + "/comando";
  topicConfig      = baseTopic + "/config";
  topicConn        = baseTopic + "/conn";

  Serial.println("Tópicos MQTT configurados:");
  Serial.println(baseTopic);

  carregarLimitesNVS();
  conectaWiFiComWiFiManager();

  if (wifiConectado) {
    reconnectMQTT();
  } else {
    Serial.println("Iniciando em modo OFFLINE (sem WiFi/MQTT).");
  }

  publicarConfigAtual(true);
  mostrarUmidadeStatus(NAN, statusUmid);

  if (TEMPO_BOOT_SEGURO_MS > 0) delay(TEMPO_BOOT_SEGURO_MS);
}

void loop() {
  // Só mexe com MQTT se tiver WiFi e MQTT habilitado
  if (wifiConectado && mqttHabilitado) {
    if (!mqttClient.connected()) reconnectMQTT();
    if (mqttClient.connected()) mqttClient.loop();
  }

  unsigned long now = millis();
  if (now - lastSensorMs >= INTERVALO_SENSOR_MS) {
    lastSensorMs = now;

    float umidade = sht30.readHumidity();

    // ===== Fail-safe de leitura (NaN) =====
    if (isnan(umidade)) {
      falhasSeguidas++;
      Serial.println("Falha leitura SHT30 (NaN)");

      if (falhasSeguidas >= FALHAS_MAX) {
        Serial.println("FAIL-SAFE: muitas falhas → DESLIGAR umidificador e desativar sistema.");
        statusUmid = 0;
        aplicarSaidaRele(statusUmid);
        publicarStatusRetido();
        sistemaAtivo = false;  // trava até comando LIGAR ou reboot
      }

      lcdSplash("Erro no", "Sensor", 600);
      return;   // não tenta controlar nada neste ciclo
    }

    // se chegou aqui, leitura é boa
    falhasSeguidas = 0;

    Serial.print("Umidade lida: ");
    Serial.println(umidade);

    publicarUmidade(umidade);
    usarHeaterSePrecisar(umidade);  // anti-condensação

    if (sistemaAtivo) {
      if (umidade < umidadeMinima && statusUmid != 1) {
        Serial.println("Umidade abaixo do mínimo → LIGAR umidificador");
        statusUmid = 1;
        momentoLigouUmidificador = millis();  // marca momento que ligou
        aplicarSaidaRele(statusUmid);
        publicarStatusRetido();
      } else if (umidade >= umidadeMaxima && statusUmid != 0) {
        Serial.println("Umidade acima do máximo → DESLIGAR umidificador");
        statusUmid = 0;
        aplicarSaidaRele(statusUmid);
        publicarStatusRetido();
      } else {
        Serial.println("Umidade dentro da faixa → mantém estado");
        aplicarSaidaRele(statusUmid);
      }
    } else {
      Serial.println("Sistema inativo. Relé desligado.");
      aplicarSaidaRele(0);
      lcd.setCursor(0, 0); lcd.print("Sistema inativo ");
      lcd.setCursor(0, 1); lcd.print("                ");
      delay(2000);
      return;
    }

    // ===== Proteção 1: muito tempo ligado sem atingir o máximo =====
    if (statusUmid == 1) {
      unsigned long tempoLigado = millis() - momentoLigouUmidificador;
      if (tempoLigado > TEMPO_MAX_LIGADO_MS && umidade < (umidadeMaxima - 2)) {
        Serial.println("PROTEÇÃO 1: Muito tempo ligado e umidade não atingiu o máximo.");
        Serial.println("Desligando umidificador e desativando sistema por segurança.");
        statusUmid = 0;
        aplicarSaidaRele(statusUmid);
        publicarStatusRetido();
        sistemaAtivo = false;
      }
    }

    // ===== Proteção 2: muito tempo com umidade >= 98% =====
    if (umidade >= 98.0) {
      if (!contandoAcima98) {
        contandoAcima98 = true;
        momentoAcima98 = millis();
        Serial.println("Proteção 2: começou contagem de umidade >= 98%.");
      } else {
        unsigned long tempoAlta = millis() - momentoAcima98;
        if (tempoAlta > TEMPO_MAX_UMID_ALTA_MS) {
          Serial.println("PROTEÇÃO 2: Umidade >= 98% por muito tempo. Desligando e desativando sistema por segurança.");
          statusUmid = 0;
          aplicarSaidaRele(statusUmid);
          publicarStatusRetido();
          sistemaAtivo = false;
        }
      }
    } else {
      if (contandoAcima98) {
        Serial.println("Proteção 2: umidade voltou a < 98%, resetando contagem.");
      }
      contandoAcima98 = false;
    }

    mostrarUmidadeStatus(umidade, statusUmid);
  }
}
