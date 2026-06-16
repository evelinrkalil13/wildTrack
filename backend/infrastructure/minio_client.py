from minio import Minio

from shared.config import get_settings

_settings = get_settings()

minio_client = Minio(
    _settings.minio_endpoint,
    access_key=_settings.minio_access_key,
    secret_key=_settings.minio_secret_key,
    secure=_settings.minio_use_ssl,
)


def check_health() -> bool:
    """Return True if MinIO responds to a list-buckets call."""
    try:
        list(minio_client.list_buckets())
        return True
    except Exception:
        return False
