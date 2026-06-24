# WebRTC ASR Runbook

Self-hosted real-time speech recognition using Moonshine v2 Medium Streaming over WebRTC.

## Architecture

```
Browser (HTTPS)
   │ getUserMedia + RTCPeerConnection
   ▼
NGINX Ingress (TLS termination)
   │ /webrtc/* → webrtc-asr service
   ▼
webrtc-asr Pod (GPU)
   │ aiortc RTCRtpReceiver
   ▼
PyAV decode ──► scipy resample 16kHz mono
   ▼
Moonshine v2 Medium Streaming
   ▼
RTCDataChannel ──► Browser transcript UI
```

## Quick Start (Local)

```bash
# 1. Install dependencies (aiortc is in pyproject.toml)
pip install -e .

# 2. Run the standalone WebRTC ASR service
MOONSHINE_WEBRTC_ENABLED=true \
RECORDINGS_DIR=./recordings \
APPLICATIONINSIGHTS_CONNECTION_STRING='' \
python -m uvicorn src.api.webrtc_main:app --host 0.0.0.0 --port 8000

# 3. Open the demo
open http://localhost:8000/static/webrtc-demo.html
```

For HTTPS in production, terminate TLS at the ingress or use a reverse proxy.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `MOONSHINE_WEBRTC_ENABLED` | `false` | Whether to load the Moonshine engine in the combined FastAPI app (`src.api.main:app`). |
| `MOONSHINE_LANGUAGE` | `en` | Model language. |
| `MOONSHINE_UPDATE_INTERVAL_MS` | `500` | Partial transcript emit interval. |
| `TURN_SERVER_URL` | — | TURN server URL (e.g., `turn:turn.example.com:3478`). |
| `TURN_SERVER_USERNAME` | — | TURN username. |
| `TURN_SERVER_CREDENTIAL` | — | TURN credential. |
| `RECORDINGS_DIR` | `/app/recordings` | Writable recordings directory. |

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health/live` | Kubernetes liveness probe |
| GET | `/health/ready` | Kubernetes readiness probe |
| GET | `/static/webrtc-demo.html` | Browser demo |
| GET | `/webrtc/ice-servers` | ICE configuration for browser |
| POST | `/webrtc/offer?session_id={id}` | SDP offer/answer exchange |

## Docker

```bash
docker build -f docker/Dockerfile.webrtc -t webrtc-asr:latest .
docker run --gpus all -p 8000:8000 webrtc-asr:latest
```

## Kubernetes

```bash
kubectl apply -k k8s/overlays/prod
```

The deployment requests one NVIDIA GPU per replica and exposes port 8000.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `No module named 'resampy'` | librosa default resampler missing | Use `scipy.signal.resample_poly` (already in code) or install `resampy`. |
| ICE state `failed` | Symmetric NAT / UDP blocked | Configure `TURN_SERVER_URL` and credentials. |
| DataChannel opens but no transcripts | Microphone permission denied or silent audio | Check browser console; ensure audio track is unmuted. |
| High latency | `MOONSHINE_UPDATE_INTERVAL_MS` too large | Lower to 250-500ms. |

## Testing

```bash
pytest tests/test_moonshine_engine.py tests/test_webrtc_routes.py -v
```
