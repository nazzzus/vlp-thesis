import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8081';

export const options = {
  vus: 1,
  iterations: 500, // Anzahl Datensätze
};

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function pick(arr) {
  return arr[randInt(0, arr.length - 1)];
}

function randomString(len) {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let out = '';
  for (let i = 0; i < len; i++) out += chars[randInt(0, chars.length - 1)];
  return out;
}

function makeDescription() {
  const bucket = randInt(1, 3); // 1=kurz, 2=mittel, 3=lang
  if (bucket === 1) return 'Gepflegtes Fahrzeug.';
  if (bucket === 2) return 'Gepflegtes Fahrzeug, technisch und optisch in gutem Zustand. Export möglich.';
  // lang (ca. 300-600 Zeichen, aber ohne Roman)
  return 'Gepflegtes Fahrzeug, technisch und optisch in gutem Zustand. Wartungen regelmäßig durchgeführt. ' +
         'Geeignet für Export, Besichtigung nach Absprache. Weitere Details und Fotos auf Anfrage. ' +
         'Ausstattung abhängig von Fahrzeugtyp, Irrtümer und Zwischenverkauf vorbehalten.';
}

export default function () {
  const makes = ['Mercedes Benz', 'MAN', 'Setra', 'Volvo', 'VDL', 'Neoplan', 'Scania'];
  const models = ['Reisebus', 'Überlandbus', 'Linienbus', 'Kleinbus'];

  const payload = JSON.stringify({
    title: `seed-${randomString(6)} ${pick(makes)} ${pick(models)}`,
    make: pick(makes),
    model: pick(models),
    year: randInt(2000, 2024),
    price: randInt(0, 200000),       // 0 erlaubt, falls "Preis auf Anfrage"
    fuel: 'Diesel',
    mileage: randInt(10000, 1500000),
    description: makeDescription(),
  });

  const res = http.post(`${BASE_URL}/vehicles`, payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, { 'status is 200/201': (r) => r.status === 200 || r.status === 201 });

  // kurze Pause, damit Atlas nicht unnötig belastet wird
  sleep(0.05);
}
