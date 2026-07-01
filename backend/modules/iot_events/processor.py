import asyncio
import logging

import aiomqtt

from infrastructure.mqtt import TOPIC_EVENTS, TOPIC_STATUS, TOPIC_TELEMETRY, extract_device_id
from modules.iot_events.service import IotEventService
from shared.config import get_settings

logger = logging.getLogger(__name__)


async def mqtt_subscriber_task() -> None:
    settings = get_settings()
    while True:
        try:
            async with aiomqtt.Client(
                hostname=settings.mqtt_host,
                port=settings.mqtt_port,
                identifier=settings.mqtt_client_id,
            ) as client:
                logger.info(
                    "MQTT connected to %s:%d as %s",
                    settings.mqtt_host,
                    settings.mqtt_port,
                    settings.mqtt_client_id,
                )
                await client.subscribe(TOPIC_EVENTS, qos=1)
                await client.subscribe(TOPIC_TELEMETRY, qos=1)
                await client.subscribe(TOPIC_STATUS, qos=1)

                async for message in client.messages:
                    topic = str(message.topic)
                    device_id = extract_device_id(topic)
                    if device_id is None:
                        logger.warning("Cannot extract device_id from topic: %s", topic)
                        continue

                    raw = message.payload
                    if isinstance(raw, str):
                        raw = raw.encode()

                    if topic.endswith("/events"):
                        asyncio.create_task(
                            IotEventService.process_feeding_event(device_id, raw)
                        )
                    elif topic.endswith("/telemetry"):
                        asyncio.create_task(
                            IotEventService.process_telemetry(device_id, raw)
                        )
                    elif topic.endswith("/status"):
                        asyncio.create_task(
                            IotEventService.process_status(device_id, raw)
                        )

        except aiomqtt.MqttError as exc:
            logger.warning("MQTT connection lost: %s — reconnecting in 5s", exc)
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("MQTT subscriber task cancelled")
            raise
