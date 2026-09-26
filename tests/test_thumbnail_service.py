import base64

from thumbnail_service import InfraiImageClient, ThumbnailVariant, publish_thumbnails


class FakeClient:
    def __init__(self):
        self.calls = []

    def upload(self, image_bytes, filename):
        self.calls.append(("upload", image_bytes, filename))
        return "img_demo"

    def resize(self, image_id, variant):
        self.calls.append(("resize", image_id, variant))
        return {"image": image_id, "width": variant.width, "height": variant.height}


def test_publish_thumbnails_makes_mobile_and_card_variants():
    client = FakeClient()
    result = publish_thumbnails(b"pixels", "dashboard.png", client)

    assert [item["width"] for item in result] == [320, 960]
    assert [item[2] for item in client.calls if item[0] == "resize"] == [
        ThumbnailVariant(320, 180), ThumbnailVariant(960, 540)
    ]


def test_http_requests_follow_image_contract():
    class Response:
        status_code = 200
        headers = {}

        def __init__(self, data):
            self.data = data

        def json(self):
            return {"ok": True, "data": self.data}

    class Session:
        def __init__(self):
            self.headers = {}
            self.calls = []

        def post(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return Response({"image_id": "img_demo"})

    session = Session()
    publish_thumbnails(b"pixels", "dashboard.png", InfraiImageClient("test", session))
    upload, *processes = session.calls
    assert upload[0].endswith("/v1/image/upload")
    assert upload[1]["json"] == {
        "file": base64.b64encode(b"pixels").decode("ascii"), "filename": "dashboard.png"
    }
    assert set(upload[1]) == {"json", "timeout"}
    for call, width, height in zip(processes, (320, 960), (180, 540)):
        assert call[0].endswith("/v1/image/process")
        assert call[1]["json"] == {
            "image": {"image_id": "img_demo"},
            "ops": [{"op": "resize", "params": {"width": width, "height": height,
                                                  "fit": "cover"}}],
            "format": "webp", "store": True,
        }
