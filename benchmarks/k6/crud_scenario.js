import http from 'k6/http';
import { check, sleep } from 'k6';

// === Konfiguration ===
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8081';

export const options = {
  vus: 10,
  duration: '60s',
  // optional: etwas besser für reproduzierbare Runs
  // thresholds: {
  //   http_req_failed: ['rate<0.01'],
  //   http_req_duration: ['p(95)<800'],
  // },
};

function randomString(len) {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let out = '';
  for (let i = 0; i < len; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}

export default function () {
  // 1) CREATE (POST /vehicles)
  const payload = JSON.stringify({
    title: `k6 test vehicle ${randomString(6)}`,
    make: 'K6',
    model: 'LoadTest',
    year: 2018,
    price: 12345,
    fuel: 'Diesel',
    mileage: 123456,
    description: 'Created by k6 CRUD baseline test',
  });

  const createRes = http.post(`${BASE_URL}/vehicles`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(createRes, {
    'CREATE status is 200/201': (r) => r.status === 200 || r.status === 201,
  });

  // Versuche, die ID aus der Response zu lesen
  let id = null;
  try {
    const body = createRes.json();
    id = body.id || body._id || null;
  } catch (e) {
    // falls keine JSON-Response oder anderes Format
  }

  // Wenn keine ID zurückkommt, brechen wir den Iterations-Flow ab,
  // damit wir nicht mit "null" weiter testen.
  if (!id) {
    // kurze Pause, damit der Loop nicht komplett eskaliert
    sleep(0.2);
    return;
  }

  // 2) READ (GET /vehicles/{id})
  const getRes = http.get(`${BASE_URL}/vehicles/${id}`);
  check(getRes, { 'READ status is 200': (r) => r.status === 200 });

  // 3) LIST (GET /vehicles?limit=50)
  const listRes = http.get(`${BASE_URL}/vehicles?limit=50`);
  check(listRes, { 'LIST status is 200': (r) => r.status === 200 });

  // 4) DELETE (DELETE /vehicles/{id})
  const delRes = http.del(`${BASE_URL}/vehicles/${id}`);
  check(delRes, {
    'DELETE status is 200/204': (r) => r.status === 200 || r.status === 204,
  });

  // kleine Pause, um zu aggressive Loops zu vermeiden
  sleep(0.2);
}
