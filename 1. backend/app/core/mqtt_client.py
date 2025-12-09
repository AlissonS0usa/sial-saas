# em algum app/core/mqtt.py, ou no próprios dispositivos.py se você preferiu
import paho.mqtt.client as mqtt
from app.services.leitura_service import processar_mensagem_mqtt

MQTT_HOST = "broker.hivemq.com"
MQTT_PORT = 1883

mqtt_client = mqtt.Client()

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print("MQTT RECEBIDO:", topic, payload)
    processar_mensagem_mqtt(topic, payload)

def on_connect(client, userdata, flags, rc):
    print("MQTT conectado, código:", rc)
    # Reassina sempre que conectar/reconectar
    client.subscribe("alissondev007/umidificador/+/telemetria")
    client.subscribe("alissondev007/umidificador/telemetria")

def start_mqtt():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
    mqtt_client.loop_start()