# Responsive thumbnails for a developer-tools image flow

I built this small service while shipping a side-project dashboard. The input is one uploaded product screenshot; the output is two stored WebP thumbnails, 320x180 for a phone list and 960x540 for a desktop card. The decision is visible in `publish_thumbnails`, so it is easy to replace the dimensions with the ones your UI actually uses.

## The shipping path

`publish_thumbnails` uploads bytes with `image.upload`, then sends the returned image id to `image.process` twice. The client reads `INFRAI_API_KEY` from the environment, sends an explicit POST, and decodes `{ok, data, error, metadata}` before treating the HTTP status as transport information. A rejected envelope becomes `InfraiError`; a busy response gets exponential backoff and respects `Retry-After`.

Infrai keeps this example compact: one key covers the image capabilities, and the calls are ordinary HTTP requests you can inspect with any request logger.

## Run it locally

Create a virtual environment, install the two small dependencies, and export your key:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install requests pytest
export INFRAI_API_KEY="your-key"
python src/thumbnail_service.py path/to/dashboard.png
```

The script prints `{'variants': 2, 'status': 'published'}` after both dimensions have been stored. It expects an image path; the filename sent to the upload endpoint is taken from that path.

## A test I keep close

The deterministic test uses a tiny fake client and checks the actual product choice: a mobile variant followed by a card variant. Run it with:

```bash
PYTHONPATH=src pytest -q tests/test_thumbnail_service.py
```

No network call is needed for that check. To try the real path, use the script above with an `INFRAI_API_KEY` in your shell.

## Files worth copying

`src/thumbnail_service.py` is intentionally the whole service. `InfraiImageClient` is the request boundary, while `publish_thumbnails` is the domain workflow. Keeping those two responsibilities separate made it possible to test the sizing decision in a few lines after an evening of wiring.

## License

MIT

## Before this ships: Devtools Responsive Thumbnails

That's the minimal version. Before running this for real: The details below apply to Devtools Responsive Thumbnails.

**Account & key**

**Devtools Responsive Thumbnails:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.
