/**
 * T0 – Baseline / Verifikation
 *
 * Zweck:  Prüft, ob alle relevanten Endpunkte des jeweiligen Deployments
 *         korrekt antworten. Keine Last, keine Auswertung – nur Smoke-Test.
 *
 * Ausführung:
 *   k6 run --env BASE_URL=https://<your-endpoint> t0_baseline.js
 */

import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL;

if (!BASE_URL) {
  throw new Error('BASE_URL ist nicht gesetzt. Beispiel: k6 run --env BASE_URL=https://... t0_baseline.js');
}

export const options = {
  vus: 1,
  iterations: 1,
};

export default function () {
  const headers = { 'Accept': 'application/json', 'Content-Type': 'application/json' };

  // 1) Health Check
  const healthRes = http.get(`${BASE_URL}/healthz`, { headers });
  check(healthRes, {
    'GET /healthz → 200': (r) => r.status === 200,
  });

  // 2) Readiness Check
  const readyRes = http.get(`${BASE_URL}/readyz`, { headers });
  check(readyRes, {
    'GET /readyz → 200': (r) => r.status === 200,
  });

  // 3) List Vehicles
  const listRes = http.get(`${BASE_URL}/vehicles?limit=50`, { headers });
  check(listRes, {
    'GET /vehicles → 200':          (r) => r.status === 200,
    'GET /vehicles → JSON-Array':   (r) => Array.isArray(JSON.parse(r.body)),
  });

  // 4) Create Vehicle
  const payload = JSON.stringify({
    title: 'T0 Baseline Test',
    make:  'K6',
    model: 'Baseline',
    year:  2020,
    price: 10000,
    fuel:  'Diesel',
    mileage: 100000,
    description: 'Automatisch erstellter Baseline-Testeintrag',
  });

  const createRes = http.post(`${BASE_URL}/vehicles`, payload, { headers });
  check(createRes, {
    'POST /vehicles → 201': (r) => r.status === 201,
  });

  // ID aus Response extrahieren und GET + DELETE prüfen
  let id = null;
  try { id = JSON.parse(createRes.body).id; } catch (_) {}

  if (id) {
    const getRes = http.get(`${BASE_URL}/vehicles/${id}`, { headers });
    check(getRes, { 'GET /vehicles/{id} → 200': (r) => r.status === 200 });

    const delRes = http.del(`${BASE_URL}/vehicles/${id}`, null, { headers });
    check(delRes, { 'DELETE /vehicles/{id} → 204': (r) => r.status === 204 });
  }
}
