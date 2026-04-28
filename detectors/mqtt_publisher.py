"""
MQTT publisher with auto-reconnect.  Runs on the EDGE DEVICE.

Publishes contract-compliant JSON events to the MQTT broker.
The broker can be on a completely different machine — set MQTT_BROKER_HOST
(or pass host= to MQTTPublisher) to the broker's IP/hostname.

Deployment model
----------------
[this module]  →  MQTT broker  →  logbase/subscriber.py
 (edge device)     (Mosquitto)      (central server)

Configuration — two equivalent ways (highest priority first):
    1. Constructor args    MQTTPublisher(host="192.168.1.100", port=1883)
    2. Environment vars    MQTT_BROKER_HOST  MQTT_BROKER_PORT

Reconnection
------------
Uses connect + loop_start.  If the broker is not reachable at startup
the publisher logs a warning and retries in the background thread via
reconnect_delay_set (1 s → 30 s).  Events published while disconnected
are buffered by paho's outgoing queue (QoS 1) and flushed on reconnect.
"""
import json
import logging
import os

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

logger = logging.getLogger(__name__)

_DEFAULT_HOST = os.getenv("MQTT_BROKER_HOST", "127.0.0.1")
_DEFAULT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
_TOPIC_PREFIX = "vforensiq/events"


class MQTTPublisher:
    def __init__(self, host: str = _DEFAULT_HOST, port: int = _DEFAULT_PORT):
        self._host = host
        self._port = port

        self._client = mqtt.Client(CallbackAPIVersion.VERSION2,
                                   client_id="vforensiq-detector",
                                   clean_session=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        # Exponential backoff: 1 s → 30 s on any disconnect or initial failure.
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            self._client.connect(host, port, keepalive=60)
        except OSError:
            logger.warning("MQTT broker %s:%d unreachable at startup — will retry", host, port)
        self._client.loop_start()
        logger.info("MQTT publisher targeting broker %s:%d", host, port)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("MQTT connected to broker %s:%d", self._host, self._port)
        else:
            logger.warning("MQTT broker refused connection (rc=%s) — will retry", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            logger.warning("MQTT disconnected from broker (rc=%s) — reconnecting", reason_code)

    def publish(self, camera_id: str, event: dict) -> None:
        topic = f"{_TOPIC_PREFIX}/{camera_id}"
        payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
        self._client.publish(topic, payload, qos=1)

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
