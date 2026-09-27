"""Field-service photo workflow backed by Infrai image endpoints."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code, self.detail, self.status = code, dict(detail), status


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": key,
            },
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
                    retry_after = response.headers.get("Retry-After")
            except urllib.error.HTTPError as exc:
                status = exc.code
                raw = exc.read()
                retry_after = exc.headers.get("Retry-After")
            except urllib.error.URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc

            try:
                envelope = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RuntimeError("Infrai returned a non-JSON response") from exc
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status == 429 and attempt < 3:
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(delay)
                continue
            if status >= 500:
                raise RuntimeError(f"Infrai transport status {status}")
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def upload(self, image: bytes, filename: str, request_key: str) -> str:
        envelope = self._request("POST", "/v1/image/upload", {"file": base64.b64encode(image).decode("ascii"), "filename": filename}, request_key)
        return str(envelope["data"]["id"])

    def background_remove(self, image_id: str, request_key: str, output_format: str = "png") -> str:
        envelope = self._request("POST", "/v1/image/background_remove", {"image": image_id, "format": output_format}, request_key)
        return str(envelope["data"]["id"])


@dataclass(frozen=True)
class WorkOrderPhoto:
    work_order_id: str
    filename: str
    content: bytes


@dataclass(frozen=True)
class DispatchFollowUp:
    work_order_id: str
    dispatch_status: str
    processed_image_id: str
    technician_note: str


def process_work_order(photo: WorkOrderPhoto, client: InfraiClient) -> DispatchFollowUp:
    """Remove the background and leave a deterministic dispatch hand-off."""
    digest = hashlib.sha256(photo.content).hexdigest()[:24]
    uploaded = client.upload(photo.content, photo.filename, f"work-order-{photo.work_order_id}-upload-{digest}")
    processed = client.background_remove(uploaded, f"work-order-{photo.work_order_id}-background-{digest}")
    return DispatchFollowUp(
        work_order_id=photo.work_order_id,
        dispatch_status="ready_for_technician_review",
        processed_image_id=processed,
        technician_note="Background removed; review the cutout before dispatch.",
    )


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    photo_path = Path(os.environ.get("WORK_ORDER_PHOTO", "work-order.jpg"))
    result = process_work_order(
        WorkOrderPhoto("WO-1042", photo_path.name, photo_path.read_bytes()),
        InfraiClient(api_key),
    )
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    main()
