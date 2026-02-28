"""
S3-compatible upload to Cloudflare R2.
Paths: artists/<handle>/thumb/001.webp, artists/<handle>/full/001.webp
"""

from typing import Optional

import boto3
from botocore.config import Config

CACHE_CONTROL = "public, max-age=31536000, immutable"
CONTENT_TYPE = "image/webp"


def _strip(val: str) -> str:
    """Strip quotes and whitespace (handles curly/smart quotes from YAML)."""
    return str(val).strip().strip('"\'"\u201c\u201d\u2018\u2019')


def get_r2_client(account_id: str, access_key_id: str, secret_access_key: str):
    """Create boto3 S3 client for R2."""
    account_id = _strip(account_id)
    access_key_id = _strip(access_key_id)
    secret_access_key = _strip(secret_access_key)
    endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        region_name="auto",
    )


def upload_image(
    client,
    bucket: str,
    handle: str,
    image_id: str,
    thumb_bytes: bytes,
    full_bytes: bytes,
) -> tuple[str, str]:
    """
    Upload thumb and full variants. Returns (thumb_key, full_key).
    Keys: artists/<handle>/thumb/001.webp, artists/<handle>/full/001.webp
    """
    thumb_key = f"artists/{handle}/thumb/{image_id}.webp"
    full_key = f"artists/{handle}/full/{image_id}.webp"

    extra = {"ContentType": CONTENT_TYPE, "CacheControl": CACHE_CONTROL}

    client.put_object(
        Bucket=bucket,
        Key=thumb_key,
        Body=thumb_bytes,
        **extra,
    )
    client.put_object(
        Bucket=bucket,
        Key=full_key,
        Body=full_bytes,
        **extra,
    )
    return thumb_key, full_key


def upload_artist_images(
    client,
    bucket: str,
    handle: str,
    image_pairs: list[tuple[bytes, bytes]],
    public_url_base: Optional[str] = None,
) -> list[dict]:
    """
    Upload all image pairs for an artist.
    Returns list of {"image_id": "001", "image_full": "artists/x/full/001.webp", "image_thumb": "..."}.
    If public_url_base is set, we store the full URL; otherwise we store the key path.
    """
    from images import format_image_id

    result = []
    for i, (thumb_b, full_b) in enumerate(image_pairs, start=1):
        image_id = format_image_id(i)
        thumb_key, full_key = upload_image(client, bucket, handle, image_id, thumb_b, full_b)
        if public_url_base:
            full_ref = f"{public_url_base.rstrip('/')}/{full_key}"
            thumb_ref = f"{public_url_base.rstrip('/')}/{thumb_key}"
        else:
            full_ref = full_key
            thumb_ref = thumb_key
        result.append({
            "image_id": image_id,
            "image_full": full_ref,
            "image_thumb": thumb_ref,
        })
    return result
