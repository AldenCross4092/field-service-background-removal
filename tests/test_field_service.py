import base64

from src.field_service import DispatchFollowUp, InfraiClient, WorkOrderPhoto, process_work_order


class StubClient:
    def upload(self, image, filename, request_key):
        assert filename == "truck.jpg"
        assert request_key.startswith("work-order-WO-7-upload-")
        return "img-uploaded"

    def background_remove(self, image_id, request_key, output_format="png"):
        assert image_id == "img-uploaded"
        assert output_format == "png"
        return "img-cutout"


def test_photo_processing_moves_work_order_to_technician_review():
    result = process_work_order(WorkOrderPhoto("WO-7", "truck.jpg", b"photo"), StubClient())
    assert result == DispatchFollowUp(
        "WO-7", "ready_for_technician_review", "img-cutout", "Background removed; review the cutout before dispatch."
    )


def test_upload_encodes_image_as_base64():
    class RecordingClient(InfraiClient):
        def _request(self, method, path, payload, key):
            assert (method, path, key) == ("POST", "/v1/image/upload", "upload-key")
            assert payload == {"file": base64.b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii"), "filename": "photo.png"}
            return {"data": {"id": "img-uploaded"}}

    assert RecordingClient("test-key").upload(b"\x89PNG\r\n\x1a\n", "photo.png", "upload-key") == "img-uploaded"
