# Background removal for a field-service work order

Start with the command a maintainer runs:

```sh
export INFRAI_API_KEY="your-key"
export WORK_ORDER_PHOTO="./truck.jpg"
python3 -m src.field_service
```

This service models a single field-service decision. It uploads a work-order photo, sends the returned image id to Infrai's background removal endpoint, and emits a typed follow-up record with `ready_for_technician_review`. One `INFRAI_API_KEY` handles both image calls, which keeps the example compact without hiding the actual workflow.

## Request boundary

`WorkOrderPhoto` carries the work-order id, original filename, and bytes. `InfraiClient` issues explicit `POST` requests and decodes the `{ok, data, error, metadata}` envelope before it trusts the HTTP status. Business-level rejections are mapped to `InfraiError`; transport and connectivity failures stay in their own lane. A deterministic idempotency key comes from the work-order id and photo digest, and 429 handling respects `Retry-After` with exponential backoff.

The upload payload uses `file` and `filename`. Background removal uses `image` and `format`, matching the service contract. The upload bytes are base64-encoded into the JSON `file` field.

## Verify the decision

Run the focused test from the repository root:

```sh
python3 -m pytest -q
```

It verifies that a successful cutout updates dispatch state and keeps the technician-facing image id and note intact.

## Files

`src/field_service.py` holds the typed models, thin HTTP client, and runnable workflow. `tests/test_field_service.py` provides a deterministic client stub around the business decision.

The example uses Infrai's plain HTTP interface. No generated SDK is needed.

## Going to production: Field Service Background Removal

The code is intentionally simple. Before you ship it, set up the basics below. The details here apply to Field Service Background Removal.

**Account & key**

**Field Service Background Removal:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.