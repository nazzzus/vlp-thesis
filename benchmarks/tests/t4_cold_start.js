/**
 * T4 – Cold-Start-Test
 *
 * Zweck:  Isoliert die Initialisierungslatenz (Cold-Start-Latenz) nach einer
 *         kontrollierten Inaktivitätsphase von 15 Minuten.
 *
 * Protokoll (manuell, 5× je Framework):
 *   1. t1_warmup.js ausführen → sichert aktive Instanzen
 *   2. 15 Minuten warten, KEIN Traffic gegen den Endpunkt
 *   3. Dieses Skript ausführen → misst erste Anfrage nach Kaltstart
 *   4. p50 aus t2-Ergebnissen als Warmzustand-Referenz (p50_warm) notieren
 *   5. ∆t_cold = t_first - p50_warm
 *   6. Schritte 1–5 insgesamt 5× wiederholen
 *
 * Zusätzliche Referenzwerte (manuell aus AWS Console / kubectl):
 *   Lambda:    CloudWatch Logs → "Init Duration" in ms
 *   OpenFaaS:  kubectl get events -n openfaas-fn | grep <function-name>
 *
 * Ausführung:
 *   k6 run --env BASE_URL=https://<your-endpoint> \
 *          --out json=results/t4_<framework>_run<n>.json \
 *          t4_cold_start.js
 */

import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL;

if (!BASE_URL) {
  throw new Error('BASE_URL ist nicht gesetzt.');
}

export const options = {
  // Genau 1 VU, 1 Iteration → misst die erste Anfrage nach Kaltstart
  vus:        1,
  iterations: 1,
  // Kein Threshold-Hard-Stop – Cold Starts können legitim langsam sein
};

export default function () {
  const start = Date.now();

  const res = http.get(`${BASE_URL}/vehicles?limit=50`, {
    headers: { 'Accept': 'application/json' },
    // Großzügiges Timeout, damit Cold Start nicht als Fehler gewertet wird
    timeout: '60s',
  });

  const duration = Date.now() - start;

  check(res, {
    'T4: status 200':           (r) => r.status === 200,
    'T4: Antwort nicht leer':   (r) => r.body && r.body.length > 2,
  });

  // Ausgabe für manuelle Protokollierung
  console.log(`T4 Cold-Start-Messung: ${duration} ms (HTTP ${res.status})`);
  console.log(`Timings: waiting=${res.timings.waiting.toFixed(1)} ms | receiving=${res.timings.receiving.toFixed(1)} ms`);
}
