import io
import json

from minio import Minio
from minio.error import S3Error

from shared.config import get_settings

_settings = get_settings()

minio_client = Minio(
    _settings.minio_endpoint,
    access_key=_settings.minio_access_key,
    secret_key=_settings.minio_secret_key,
    secure=_settings.minio_use_ssl,
)

_PUBLIC_READ_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{_settings.minio_bucket}/*"],
        }
    ],
}


def ensure_bucket_public() -> None:
    """Create the media bucket if it doesn't exist and apply public-read policy."""
    if not minio_client.bucket_exists(_settings.minio_bucket):
        minio_client.make_bucket(_settings.minio_bucket)
    minio_client.set_bucket_policy(
        _settings.minio_bucket, json.dumps(_PUBLIC_READ_POLICY)
    )


def upload_jpeg(object_name: str, data: bytes) -> str:
    """Upload raw JPEG bytes and return the public URL."""
    minio_client.put_object(
        _settings.minio_bucket,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type="image/jpeg",
    )
    base = f"http://{_settings.minio_endpoint}"
    return f"{base}/{_settings.minio_bucket}/{object_name}"


def check_health() -> bool:
    """Return True if MinIO responds to a list-buckets call."""
    try:
        list(minio_client.list_buckets())
        return True
    except Exception:
        return False
