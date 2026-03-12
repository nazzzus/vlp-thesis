import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL;
if (!BASE_URL) throw new Error('BASE_URL ist nicht gesetzt.');

export const options = {
  stages: [
    { duration: '1m', target: 10 },  // Sanfter Einstieg – Lambda-Instanzen starten
    { duration: '1m', target: 30 },  // Auf Ziellast hochfahren
    { duration: '1m', target: 30 },  // Stabil halten
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],   // Toleranter während Warm-up
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/vehicles?limit=50`, {
    headers: { 'Accept': 'application/json' },
  });
  check(res, { 'Warm-up: status 200': (r) => r.status === 200 });
  sleep(0.5);
}
