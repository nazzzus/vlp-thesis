/**
 * T3 – Ramp-Test (Skalierungsverhalten)
 *
 * Zweck:  Untersucht das Skalierungsverhalten der Frameworks unter stufenweise
 *         steigender Last. Identifiziert den Punkt, ab dem Fehlerraten oder
 *         Antwortzeiten signifikant ansteigen.
 *
 * Lastprofil:
 *   Anlauf  2 min   0 → 10 VU  (sanfter Einstieg)
 *   Stufe 1 3 min  10 VU        (geringe Last)
 *   Stufe 2 3 min  25 VU        (mittlere Last)
 *   Stufe 3 3 min  50 VU        (hohe Last)
 *   Auslauf 1 min  50 → 0 VU   (kontrolliertes Herunterfahren)
 *
 * Hinweis: Maximallast bewusst auf 50 VU begrenzt (identisch mit T2),
 *          um Infrastruktureffekte bei OpenFaaS (feste Pod-Anzahl) nicht
 *          zu dominieren und Vergleichbarkeit zu erhalten.
 *
 * Ausführung:
 *   k6 run --env BASE_URL=https://<your-endpoint> \
 *          --out json=results/t3_<framework>.json \
 *          t3_ramp.js
 *
 * Hinweis: T3 wird einmalig pro Framework ausgeführt (kein dreifaches
 *          Wiederholen wie T2), da das Skalierungsverhalten qualitativ
 *          bewertet wird.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL;

if (!BASE_URL) {
  throw new Error('BASE_URL ist nicht gesetzt.');
}

export const options = {
  scenarios: {
    ramp: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 10 }, // Anlauf
        { duration: '3m', target: 10 }, // Stufe 1 – geringe Last
        { duration: '3m', target: 25 }, // Stufe 2 – mittlere Last
        { duration: '3m', target: 50 }, // Stufe 3 – hohe Last
        { duration: '1m', target:  0 }, // Auslauf
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    // Kapazitätsgrenze: Fehlerrate > 1 % oder p95 verdoppelt sich → im
    // Ergebniskapitel gesondert ausweisen (kein automatischer Abbruch)
    http_req_failed: ['rate<0.05'],
  },
};

const MAKES  = ['Mercedes Benz', 'MAN', 'Setra', 'Volvo', 'Neoplan'];
const MODELS = ['Reisebus', 'Linienbus', 'Kleinbus'];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// Anfragenmix identisch mit T2: 70 % GET, 30 % POST
const GET_RATIO = 0.70;

export default function () {
  const headers = {
    'Accept':       'application/json',
    'Content-Type': 'application/json',
  };

  if (Math.random() < GET_RATIO) {
    const res = http.get(`${BASE_URL}/vehicles?limit=50`, {
      headers,
      tags: { type: 'GET' },
    });

    check(res, {
      'GET /vehicles → 200':   (r) => r.status === 200,
    });

  } else {
    const payload = JSON.stringify({
      title:       `T3-${pick(MAKES)}-${randInt(1000, 9999)}`,
      make:         pick(MAKES),
      model:        pick(MODELS),
      year:         randInt(2000, 2024),
      price:        randInt(5000, 150000),
      fuel:        'Diesel',
      mileage:      randInt(10000, 800000),
      description: 'Erstellt durch k6 T3-Ramp-Test.',
    });

    const res = http.post(`${BASE_URL}/vehicles`, payload, {
      headers,
      tags: { type: 'POST' },
    });

    check(res, {
      'POST /vehicles → 201': (r) => r.status === 201,
    });
  }

  sleep(0.1);
}
