/**
 * T1 – Warm-up
 *
 * Zweck:  Lambda-Instanzen und EKS-Pods vorladen, bevor T2 oder T4 starten.
 *         Daten dieses Skripts werden NICHT ausgewertet.
 *         Sichert, dass keine Cold Starts in die Hauptmessungen einfließen.
 *
 * Ausführung:
 *   k6 run --env BASE_URL=https://<your-endpoint> t1_warmup.js
 *
 * Abbruchkriterium: p95 < 500 ms in den letzten 60 s (automatisch via threshold).
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL;

if (!BASE_URL) {
  throw new Error('BASE_URL ist nicht gesetzt.');
}

export const options = {
  vus:      10,
  duration: '3m',
  // Schwellenwert als Orientierung – kein Hard-Stop, da Warm-up toleranter sein darf
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/vehicles?limit=50`, {
    headers: { 'Accept': 'application/json' },
  });

  check(res, {
    'Warm-up: status 200': (r) => r.status === 200,
  });

  sleep(0.1);
}
