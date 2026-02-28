"""
Download images, convert to WEBP, create thumb (400px) and full (1600px) variants.
"""

import io
import time
import random
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
import requests

from fetch import create_session, get_with_retry

THUMB_WIDTH = 400
FULL_MAX_WIDTH = 1600
WEBP_QUALITY = 85
MAX_RETRIES = 3
RETRY_BACKOFF = (1, 3, 9)


def _download_image(session, url: str) -> Optional[bytes]:
    """Download image with retries."""
    for attempt, backoff in enumerate(RETRY_BACKOFF):
        try:
            resp = get_with_retry(
                session,
                url,
                timeout=15,
                extra_delay_after=0.3 if attempt == 0 else None,
            )
            data = resp.content
            if len(data) > 0:
                return data
        except Exception as e:
            if attempt < len(RETRY_BACKOFF) - 1:
                time.sleep(backoff)
            else:
                raise RuntimeError(f"Failed to download {url}: {e}") from e
    return None


def _process_image(data: bytes, thumb_width: int, full_width: int) -> tuple[bytes, bytes]:
    """
    Convert to WEBP, produce thumb and full variants. Strips EXIF.
    Returns (thumb_bytes, full_bytes).
    """
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")

    # Strip EXIF
    img_no_exif = Image.new("RGB", img.size)
    img_no_exif.putdata(list(img.getdata()))

    def resize_if_needed(w, max_w):
        if w <= max_w:
            return img_no_exif
        ratio = max_w / w
        new_h = int(img_no_exif.height * ratio)
        return img_no_exif.resize((max_w, new_h), Image.Resampling.LANCZOS)

    thumb_img = resize_if_needed(img_no_exif.width, thumb_width)
    full_img = resize_if_needed(img_no_exif.width, full_width)

    thumb_buf = io.BytesIO()
    full_buf = io.BytesIO()
    thumb_img.save(thumb_buf, "WEBP", quality=WEBP_QUALITY)
    full_img.save(full_buf, "WEBP", quality=WEBP_QUALITY)

    return thumb_buf.getvalue(), full_buf.getvalue()


def download_and_process_images(
    urls: list[str],
    max_concurrent: int = 10,
    thumb_width: int = THUMB_WIDTH,
    full_width: int = FULL_MAX_WIDTH,
) -> list[tuple[bytes, bytes]]:
    """
    Download images and return list of (thumb_bytes, full_bytes).
    Skips failed downloads; order may not match input.
    """
    session = create_session()
    results = []

    def process_one(idx_url):
        idx, url = idx_url
        try:
            data = _download_image(session, url)
            if data:
                return (idx, _process_image(data, thumb_width, full_width))
        except Exception as e:
            return (idx, None)
        return (idx, None)

    with ThreadPoolExecutor(max_workers=max_concurrent) as ex:
        futures = {ex.submit(process_one, (i, u)): (i, u) for i, u in enumerate(urls)}
        completed = {}
        for f in as_completed(futures):
            idx, pair = f.result()
            if pair:
                completed[idx] = pair

    for i in range(len(urls)):
        if i in completed:
            results.append(completed[i])

    return results


def format_image_id(n: int) -> str:
    """Zero-pad to 3 digits: 001, 002, ..."""
    return f"{n:03d}"
