"""Image encode/decode/resize helpers."""

from __future__ import annotations

import base64

import cv2
import numpy as np


def encode_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
    """Encode a BGR frame to JPEG bytes."""
    params = [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)]
    ok, buffer = cv2.imencode(".jpg", frame, params)
    if not ok:
        raise ValueError("Failed to JPEG-encode frame")
    return buffer.tobytes()


def encode_jpeg_base64(frame: np.ndarray, quality: int = 80) -> str:
    """Encode a BGR frame to a base64 data-URI string (for WebSocket/JSON)."""
    raw = encode_jpeg(frame, quality)
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


def decode_image(data: bytes) -> np.ndarray:
    """Decode image bytes into a BGR frame."""
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Failed to decode image bytes")
    return frame


def resize_keep(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    """Resize a frame to (width, height) if it differs."""
    h, w = frame.shape[:2]
    if (w, h) == (width, height):
        return frame
    return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
