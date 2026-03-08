import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8081';

// Deterministischer Pseudo-Zufallsgenerator (fester Seed = reproduzierbar)
let seedState = 42;
function seededRand() {
  seedState = (seedState * 1664525 + 1013904223) & 0xffffffff;
  return (seedState >>> 0) / 0xffffffff;
}

function randInt(min, max) {
  return Math.floor(seededRand() * (max - min + 1)) + min;
}

function pick(arr) {
  return arr[randInt(0, arr.length - 1)];
}

export const options = {
  vus: 1,
  iterations: 500,
};

export default function () {
  const makes  = ['Mercedes Benz', 'MAN', 'Setra', 'Volvo', 'VDL', 'Neoplan', 'Scania'];
  const models = ['Reisebus', 'Überlandbus', 'Linienbus', 'Kleinbus'];

  const i = __ITER;  // k6 built-in: aktuelle Iteration (0-499)

  const payload = JSON.stringify({
    title:       `seed-${String(i).padStart(4,'0')} ${pick(makes)} ${pick(models)}`,
    make:         pick(makes),
    model:        pick(models),
    year:         randInt(2000, 2024),
    price:        randInt(5000, 200000),
    fuel:        'Diesel',
    mileage:      randInt(10000, 1500000),
    description: 'Seed-Datensatz für VLP-Vergleichsstudie. Iteration ' + i,
  });

  const res = http.post(`${BASE_URL}/vehicles`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, { 'seed: status 201': (r) => r.status === 201 });
  sleep(0.05);
}