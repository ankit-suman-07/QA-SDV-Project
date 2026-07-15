# Vehicle Health Dashboard — Iteration 1

This frontend is a contract-driven dashboard prototype for `vehicle-001`. It currently uses mock JSON responses that follow `docs/04-vehicle-health-contracts.md` because the Spring Boot vehicle API is not implemented in this repository snapshot.

## Run

```bash
cd frontend
python3 -m http.server 5500
```

Open `http://localhost:5500`.

Use the demo-state selector to validate HEALTHY, WARNING, CRITICAL, RECOVERED, DISCONNECTED, and ERROR states.

## Test

```bash
cd frontend
npm install
npm test
```

## Backend integration handoff

When the backend exposes `GET /api/vehicles/vehicle-001`, change the call in `js/dashboard.js` from mock mode to API mode:

```js
const state = await getVehicleState({ mode: "api" });
```

Remove or hide the demo selector for the integrated demonstration. The API response must follow the shared vehicle health contract or the frontend mapping must be updated explicitly.
