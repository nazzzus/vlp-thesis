/**
 * T2 – Konstantlast (Hauptmessung)
 *
 * Zweck:  Misst Steady-State-Performance unter definierter, gleichbleibender
 *         Last. Dies ist das zentrale Szenario für den Framework-Vergleich.
 *
 * Anfragenmix:
 *   70 % GET  /vehicles?limit=50   (typische Leseoperationen)
 *   30 % POST /vehicles            (Schreiboperationen)
 *
 * Parameter:
 *   VUs:       50 (konstant)
 *   Dauer:     10 Minuten
 *   Wiederholungen: 3× pro Framework (manuell, mit ≥ 10 min Pause dazwischen)
 *
 * Ausführung:
 *   k6 run --env BASE_URL=https://<your-endpoint> \
 *          --out json=results/t2_<framework>_run<n>.json \
 *          t2_constant_load.js
 *
 * Hinweis: Vor jedem Run t1_warmup.js ausführen und Daten verwerfen.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL;

if (!BASE_URL) {
  throw new Error('BASE_URL ist nicht gesetzt.');
}

// Anfragenmix: 70 % GET, 30 % POST
// Realisiert über Zufallswert je Iteration
const GET_RATIO = 0.70;

export const options = {
  vus:      10,
  duration: '10m',
  thresholds: {
    // Fehlerrate unter 1 % – Überschreitung macht Run ungültig (→ wiederholen)
    http_req_failed:                    ['rate<0.01'],
    // Orientierungswert; kein Hard-Stop
    'http_req_duration{type:GET}':      ['p(95)<2000'],
    'http_req_duration{type:POST}':     ['p(95)<3000'],
  },
};

// Seed-Daten für POST-Requests
const MAKES   = ['Mercedes Benz', 'MAN', 'Setra', 'Volvo', 'Neoplan', 'Scania'];
const MODELS  = ['Reisebus', 'Überlandbus', 'Linienbus', 'Kleinbus'];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export default function () {
  const headers = {
    'Accept':       'application/json',
    'Content-Type': 'application/json',
  };

  if (Math.random() < GET_RATIO) {
    // ── GET /vehicles?limit=50 ──────────────────────────────────────────────
    const res = http.get(`${BASE_URL}/vehicles?limit=50`, {
      headers,
      tags: { type: 'GET' },
    });

    check(res, {
      'GET /vehicles → 200':        (r) => r.status === 200,
      'GET /vehicles → Array':      (r) => {
        try { return Array.isArray(JSON.parse(r.body)); }
        catch (_) { return false; }
      },
    });

  } else {
    // ── POST /vehicles ──────────────────────────────────────────────────────
    const payload = JSON.stringify({
      title:       `T2-${pick(MAKES)}-${randInt(1000, 9999)}`,
      make:         pick(MAKES),
      model:        pick(MODELS),
      year:         randInt(2000, 2024),
      price:        randInt(5000, 150000),
      fuel:        'Diesel',
      mileage:      randInt(10000, 800000),
      description: 'Erstellt durch k6 T2-Konstantlasttest.',
    });

    const res = http.post(`${BASE_URL}/vehicles`, payload, {
      headers,
      tags: { type: 'POST' },
    });

    check(res, {
      'POST /vehicles → 201': (r) => r.status === 201,
    });
  }

  // Kurze Pause verhindert busyloop; hält das Profil realistisch
  sleep(0.1);
}
