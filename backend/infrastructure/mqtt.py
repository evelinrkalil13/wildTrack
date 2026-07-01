TOPIC_EVENTS = "wildtrack/devices/+/events"
TOPIC_TELEMETRY = "wildtrack/devices/+/telemetry"
TOPIC_STATUS = "wildtrack/devices/+/status"


def extract_device_id(topic: str) -> str | None:
    """Extract device_id from 'wildtrack/devices/{device_id}/{suffix}'."""
    parts = topic.split("/")
    if len(parts) == 4 and parts[0] == "wildtrack" and parts[1] == "devices":
        return parts[2]
    return None
