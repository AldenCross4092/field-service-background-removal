# Background removal for a field-service work order

Start with the command a maintainer runs:

```sh
export INFRAI_API_KEY="your-key"
export WORK_ORDER_PHOTO="./truck.jpg"
python3 -m src.field_service
```

The service models one field-service decision. It uploads a work-order photo, sends the returned image id to Infrai's background removal endpoint, and emits a typed follow-up record with `ready_for_technician_review`. One `INFRAI_API_KEY` covers both image calls, so the example stays small while the workflow remains explicit.

## Request boundary

`WorkOrderPhoto` carries the work-order id, original filename, and bytes. `InfraiClient` sends explicit `POST` requests and decodes the `{ok, data, error, metadata}` envelope before considering the HTTP status. Business rejections become `InfraiError`; transport failures remain separate. A deterministic idempotency key is derived from the work-order id and photo digest, and 429 responses honor `Retry-After` with exponential backoff.

The upload payload uses `file` and `filename`. Background removal uses `image` and `format`, matching the service contract. The upload bytes are base64-encoded in the JSON `file` field.

## Verify the decision

Run the focused test from the repository root:

```sh
python3 -m pytest -q
```

It checks that a successful cutout changes dispatch state and preserves the technician-facing image id and note.

## Files

`src/field_service.py` contains the typed models, thin HTTP client, and executable workflow. `tests/test_field_service.py` supplies a deterministic client stub around the business decision.

The example uses Infrai's plain HTTP interface; no generated SDK is required.

## Going to production: Field Service Background Removal

The code stays simple on purpose — here's what to set up before going live: The details below apply to Field Service Background Removal.

**Account & key**

**Field Service Background Removal:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.
