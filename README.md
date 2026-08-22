# stanCodeFinalProject

Brain AI Visualizer built with Vue 3, TypeScript, Vite, TresJS, and Three.js.

The cognitive prediction contract accepts exactly `relaxed_openeye`,
`concentration`, and `relaxed_closeeye`. Product UI renders these as
**Relaxed · Eyes Open**, **Concentration**, and **Relaxed · Eyes Closed**.
FaceCap uses separate internal visual states: `idle`, `relaxedOpenEye`,
`focused`, and `relaxedCloseEye`.

## Frontend development

```powershell
npm install
npm run dev
```

The frontend has one active data source at a time:

```dotenv
VITE_BRAIN_DATA_SOURCE=mock
```

or:

```dotenv
VITE_BRAIN_DATA_SOURCE=websocket
VITE_REALTIME_WS_URL=ws://localhost:8000/ws
```

Resolution order for the realtime endpoint is:

1. Runtime query parameter `?ws=`
2. The last valid query URL saved in local storage
3. `VITE_REALTIME_WS_URL`
4. `ws://localhost:8000/ws` in local HTTP development only

For example, a deployed HTTPS frontend can connect to a temporary WSS endpoint
without rebuilding:

```text
https://frontend.example/?ws=wss%3A%2F%2FPUBLIC_HOST%2Fws
```

HTTPS pages reject insecure `ws://` endpoints. A production build with no
configured endpoint shows `Realtime endpoint not configured` and does not fall
back to localhost. A successful `?ws=` override is persisted for later visits.

## Validation

```powershell
npm run test:frontend
npm run build
```

Append `?cognitiveDebug=1` to the local development URL to cycle the FaceCap
through `relaxedOpenEye`, `focused`, and `relaxedCloseEye` every three seconds.

With the synthetic backend already running, exercise the actual frontend
WebSocket service, validators, and Pinia state using:

```powershell
npm run smoke:frontend-realtime
```
