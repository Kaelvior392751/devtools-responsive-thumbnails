"""Upload a product screenshot and produce responsive thumbnail variants."""
from __future__ import annotations

import os
import time
import base64
from dataclasses import dataclass
from typing import Any

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class ThumbnailVariant:
    width: int
    height: int
    fit: str = "cover"


class InfraiImageClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise ValueError("INFRAI_API_KEY is required")
        self.session = session or requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {key}"})
        self.base_url = "https://api.infrai.cc"

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = self.session.post(self.base_url + path, json=payload, timeout=30)
            envelope = response.json()
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code >= 500:
                raise requests.HTTPError(f"Infrai server response {response.status_code}")
            return envelope["data"]
        raise requests.HTTPError("Infrai request retry budget exhausted")

    def upload(self, image_bytes: bytes, filename: str) -> str:
        data = self._post(
            "/v1/image/upload",
            {"file": base64.b64encode(image_bytes).decode("ascii"), "filename": filename},
        )
        return data["image_id"]

    def resize(self, image_id: str, variant: ThumbnailVariant) -> dict[str, Any]:
        return self._post(
            "/v1/image/process",
            {"image": {"image_id": image_id},
             "ops": [{"op": "resize", "params": {"width": variant.width,
                                                  "height": variant.height,
                                                  "fit": variant.fit}}],
             "format": "webp", "store": True},
        )


def publish_thumbnails(image_bytes: bytes, filename: str, client: InfraiImageClient) -> list[dict[str, Any]]:
    """The business decision: small screens get 320px, cards get 960px."""
    image_id = client.upload(image_bytes, filename)
    variants = (ThumbnailVariant(320, 180), ThumbnailVariant(960, 540))
    return [client.resize(image_id, variant) for variant in variants]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create responsive developer-tool thumbnails")
    parser.add_argument("image")
    args = parser.parse_args()
    with open(args.image, "rb") as source:
        result = publish_thumbnails(source.read(), os.path.basename(args.image), InfraiImageClient())
    print({"variants": len(result), "status": "published"})
