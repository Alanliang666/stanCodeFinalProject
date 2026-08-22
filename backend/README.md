# Muse 2 EEG backend

Phase 1 provides BrainFlow acquisition, a variable-chunk EEG contract, a
configurable inference buffer, and timestamp validation. Phase 2 connects valid
windows to a provider abstraction and validates cognitive prediction output.
Phase 3 exposes the Local Realtime Agent over HTTP and WebSocket. The current
runtime uses an explicitly labeled stub and does not contain a trained model.

## Environment

From the repository root:

```powershell
python -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

## Hardware development runtime

Turn on the Muse 2 and ensure it is available to the operating system, then
run from the repository root:

```powershell
python -m backend.app.main
```

BrainFlow can autodiscover a Muse 2. If discovery is ambiguous, specify one of
the optional identifiers:

```powershell
python -m backend.app.main --mac-address "AA:BB:CC:DD:EE:FF"
python -m backend.app.main --serial-number "Muse-XXXX"
```

Stop the development runtime with `Ctrl+C`. Session stop and release run in a
`finally` block. The runtime then prints a Phase 1 diagnostic summary containing
chunk-size distribution, sample/window totals, PASS rate, window-duration and
continuous timestamp-interval statistics, and counts above 1.5x and 2.0x the
expected sample interval. FAIL events also print their reason and maximum gap.

The current development runtime prints `STUB MODEL` during startup. Its
time-based three-state demo advances every three seconds and only verifies
wiring; it must not be interpreted as a real cognitive prediction or as an
inference from the EEG values.

## Model Team Integration Contract

The Backend passes only an `EEGWindowValidator`-approved raw window to the model
provider.

### Inference window configuration

The inference branch reads its window and stride once at runtime from centralized
`EEGInferenceConfig`. The defaults preserve the existing one-second,
non-overlapping behavior:

```powershell
$env:EEG_WINDOW_SAMPLES = "256"
$env:EEG_STRIDE_SAMPLES = "256"
```

For a two-second non-overlapping model:

```powershell
$env:EEG_WINDOW_SAMPLES = "512"
$env:EEG_STRIDE_SAMPLES = "512"
```

For a two-second window with a prediction hop every one second:

```powershell
$env:EEG_WINDOW_SAMPLES = "512"
$env:EEG_STRIDE_SAMPLES = "256"
```

`EEG_WINDOW_SAMPLES` is how much EEG each inference sees.
`EEG_STRIDE_SAMPLES` is how many samples the buffer advances before producing
the next inference window. Both units are samples. Sampling remains fixed at
256 Hz, so their displayed durations are derived by dividing by 256.

Both values must be positive integers and stride must not exceed window size.
The source-side `eeg_chunk` remains a variable-size `(N, 4)` message; these
settings only affect inference aggregation.

Input:

```text
type: numpy.ndarray
shape: (EEG_WINDOW_SAMPLES, 4)
sampling rate: 256 Hz
window duration: EEG_WINDOW_SAMPLES / 256 seconds
column 0: TP9
column 1: AF7
column 2: AF8
column 3: TP10
```

Output:

```json
{
  "state": "concentration",
  "confidence": 0.88,
  "probabilities": {
    "relaxed_openeye": 0.06,
    "concentration": 0.88,
    "relaxed_closeeye": 0.06
  }
}
```

The accepted states and exact probability keys are `relaxed_openeye`,
`concentration`, and `relaxed_closeeye`. Missing or additional classes are
invalid model output.

Probabilities must sum to approximately 1. `state` must be a highest-probability
class, and `confidence` must equal `probabilities[state]` within floating-point
tolerance.

The Model Team's `predict_mental_state(raw_window)` function owns all filtering,
preprocessing, feature extraction, fitted scaler usage, model execution, and
`predict_proba`. The Backend does not reproduce any of those operations.

The provider receives a writable NumPy copy. Mutating it cannot modify the
immutable `EEGChunk` retained by the Backend.

### Runtime model provider

`MODEL_PROVIDER` selects the model independently from the EEG source:

```powershell
$env:MODEL_PROVIDER = "stub"
python -m backend.app.server --synthetic
```

```powershell
$env:MODEL_PROVIDER = "model_team"
python -m backend.app.server
```

The supported values are exactly `stub` and `model_team`; the default is
`stub`. Synthetic EEG does not imply a stub model, so this wiring test is also
supported:

```powershell
$env:MODEL_PROVIDER = "model_team"
python -m backend.app.server --synthetic
```

`model_team` lazily imports the following package-relative callable once during
runtime startup:

```python
from backend.app.model.inference import predict_mental_state
```

The Model Team must install its implementation and artifacts under
`backend/app/model/`, with this entry point:

```python
def predict_mental_state(raw_window: numpy.ndarray) -> Mapping[str, object]:
    ...
```

The module should load its model, scaler, and other immutable artifacts once at
module import or provider initialization—not once per EEG window. It owns all
preprocessing and must return the three-class output contract above.

The Model Team may optionally declare its accepted input sizes in the inference
module:

```python
SUPPORTED_WINDOW_SAMPLES = (512,)
```

Multiple sizes are allowed, for example `(256, 512)`. A model that supports only
one size may instead declare `WINDOW_SIZE_SAMPLES = 512`. When metadata is
present, startup fails if `EEG_WINDOW_SAMPLES` is incompatible. The Backend does
not pad, truncate, reshape, or fall back to the stub. Metadata is optional until
the Model Team package provides it.

The repository currently does not contain `backend/app/model/inference.py` or
trained artifacts. Selecting `MODEL_PROVIDER=model_team` before installing them
fails at startup with:

```text
REAL MODEL LOAD FAILED
Model Team inference package is not installed.
Expected callable:
backend.app.model.inference.predict_mental_state
```

There is deliberately no fallback to `STUB MODEL`. Single-call exceptions after
a real provider has loaded are converted to `ModelExecutionError`; acquisition
continues and the bad window is not published. Raw model output still passes
through `CognitivePrediction` validation before reaching the realtime layer.

The successful real provider is reported as
`MODEL TEAM - predict_mental_state` in startup logs and `/health`.

## Unit tests

The tests do not import BrainFlow and do not require Muse hardware:

```powershell
python -m unittest discover -s backend/tests -v
```

## Local Realtime Agent

The Local Agent runs Muse acquisition, model inference, and the FastAPI server
in one Python process. The existing `python -m backend.app.main` diagnostic
runtime remains available and unchanged.

Install dependencies in the workspace environment:

```powershell
python -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

Run with a real Muse 2:

```powershell
python -m backend.app.server
```

Optional device selection:

```powershell
python -m backend.app.server --mac-address "AA:BB:CC:DD:EE:FF"
python -m backend.app.server --serial-number "Muse-XXXX"
```

The defaults are `0.0.0.0:8000`, `GET /health`, and WebSocket `/ws`. Host and
port can be configured without changing source code:

```powershell
python -m backend.app.server --host 127.0.0.1 --port 8000
$env:LOCAL_AGENT_HOST = "127.0.0.1"
$env:LOCAL_AGENT_PORT = "8000"
python -m backend.app.server
```

Check health:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

The response contains only service/device/model-provider status and never raw
EEG:

```json
{
  "status": "ok",
  "device_connected": true,
  "model_provider": "STUB MODEL",
  "sampling_rate_hz": 256,
  "inference_window_samples": 512,
  "inference_window_sec": 2.0,
  "inference_stride_samples": 256,
  "inference_stride_sec": 1.0
}
```

### Synthetic transport smoke test

Terminal 1:

```powershell
python -m backend.app.server --synthetic
```

This mode is labeled `MOCK / SYNTHETIC STREAM` and does not use BrainFlow or
physical Muse hardware.

Terminal 2:

```powershell
python -m backend.app.smoke_client --url ws://localhost:8000/ws --messages 12
```

The receive-only client prints message types and EEG sample counts, not complete
EEG arrays. It should observe `device_status`, variable-size `eeg_chunk`
messages, and the current `STUB MODEL` cognitive prediction.

### Realtime delivery and backpressure

The synchronous Muse thread publishes to a thread-safe latest-only handoff with
at most one pending message of each type. An async dispatcher transfers those
messages to `WebSocketManager`; it never sends to browsers from the acquisition
thread.

Each browser has an independent sender task and an independent latest-only
buffer. Device status and prediction are delivered before EEG. If a browser is
slow, older pending EEG is replaced by the newest chunk. A slow or disconnected
browser therefore cannot block Muse acquisition, model inference, or another
browser. New clients immediately receive current device status and, when
available, the latest prediction. EEG history is not retained.

The browser side is receive-only in this phase. Incoming WebSocket text is
ignored and there are no remote Muse/model control commands.

### External tunnel layer

A future tunnel may forward public traffic to `localhost:8000`, but it is an
external deployment layer. The Backend contains no Cloudflare import, SDK,
hostname, API, or tunnel lifecycle logic. Replacing the tunnel or transport does
not change Muse acquisition, EEG buffering/validation, model inference, or the
realtime message contracts.

### Public Tunnel Smoke Test

Start the explicitly labeled synthetic backend first:

```powershell
backend\.venv\Scripts\python.exe -m backend.app.server --synthetic
```

In a second terminal, expose the local HTTP server with the separately installed
`cloudflared` CLI:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Copy the temporary hostname printed by that process; do not hardcode it in the
repository. Verify HTTP health and then the WSS stream:

```powershell
Invoke-RestMethod https://PUBLIC_HOST/health
backend\.venv\Scripts\python.exe -m backend.app.smoke_client --url wss://PUBLIC_HOST/ws --messages 12
```

The tunnel is optional deployment infrastructure. No Cloudflare SDK or tunnel
lifecycle code is imported by the backend.
