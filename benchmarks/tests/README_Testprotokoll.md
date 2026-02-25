# k6 Testprotokolle – VLP Serverless Framework Vergleich

## Voraussetzungen

- k6 v0.52.0 installiert
- Alle drei Deployments laufen in eu-central-1
- Umgebungsvariablen für die Endpunkt-URLs verfügbar

```bash
export SAM_URL=https://<api-id>.execute-api.eu-central-1.amazonaws.com/prod
export SLS_URL=https://<api-id>.execute-api.eu-central-1.amazonaws.com/prod
export FAAS_URL=https://<alb-dns-name>
```

---

## Vorbereitung vor allen Tests (einmalig)

Datenbankzustand zurücksetzen (500 Einträge, deterministischer Seed):
```bash
k6 run --env BASE_URL=$SAM_URL \
       --vus 1 --iterations 500 \
       ../seed_vehicles.js
# gleiches Skript für $SLS_URL und $FAAS_URL
```

---

## Ausführungsreihenfolge (strikt einhalten)

### Schritt 1 – T0: Verifikation (einmalig pro Framework)

```bash
k6 run --env BASE_URL=$SAM_URL  t0_baseline.js
k6 run --env BASE_URL=$SLS_URL  t0_baseline.js
k6 run --env BASE_URL=$FAAS_URL t0_baseline.js
```

Alle Checks müssen grün sein. Erst dann weitermachen.

---

### Schritt 2 – T4: Cold-Start-Tests (5× je Framework)

Protokoll je Wiederholung (5×):
```bash
# 1. Warm-up
k6 run --env BASE_URL=$SAM_URL t1_warmup.js
# 2. Warten – EXAKT 15 Minuten, KEIN Traffic
sleep 900
# 3. Cold-Start-Messung
k6 run --env BASE_URL=$SAM_URL \
       --out json=results/t4_sam_run1.json \
       t4_cold_start.js
```

Dasselbe für `$SLS_URL` und `$FAAS_URL`.

Zwischen den Frameworks mindestens 10 Minuten Pause.

**Lambda-Referenzwert:** Nach jedem T4-Run in CloudWatch Logs nachschlagen:
```
filter @type = "REPORT"
| fields @duration, @initDuration
| sort @timestamp desc
| limit 5
```
`initDuration`-Wert manuell in Protokollbogen eintragen.

**OpenFaaS-Referenzwert:**
```bash
kubectl get events -n openfaas-fn --sort-by='.lastTimestamp' | tail -20
```

---

### Schritt 3 – T2: Konstantlast (3× je Framework, Hauptmessung)

```bash
# Run 1 – SAM
k6 run --env BASE_URL=$SAM_URL t1_warmup.js          # Warm-up, Daten verwerfen
k6 run --env BASE_URL=$SAM_URL \
       --out json=results/t2_sam_run1.json \
       t2_constant_load.js

# 10 Minuten Pause
sleep 600

# Run 2 – SAM
k6 run --env BASE_URL=$SAM_URL t1_warmup.js
k6 run --env BASE_URL=$SAM_URL \
       --out json=results/t2_sam_run2.json \
       t2_constant_load.js

# 10 Minuten Pause
sleep 600

# Run 3 – SAM
k6 run --env BASE_URL=$SAM_URL t1_warmup.js
k6 run --env BASE_URL=$SAM_URL \
       --out json=results/t2_sam_run3.json \
       t2_constant_load.js
```

Dasselbe Schema für `$SLS_URL` (→ t2_sls_run1/2/3.json)
und `$FAAS_URL` (→ t2_faas_run1/2/3.json).

Zwischen den Frameworks mindestens 10 Minuten Pause.

---

## Ungültigkeitskriterien (Run wiederholen wenn):

- Fehlerrate `http_req_failed > 1 %`
- Variationskoeffizient CV = σ/x̄ > 0.15 (nach Auswertung prüfen)
- Externe Störung protokolliert (AWS-Incident, Netzwerkproblem)

---

## Ergebnisstruktur

```
results/
  t0_sam.json
  t0_sls.json
  t0_faas.json
  t2_sam_run1.json
  t2_sam_run2.json
  t2_sam_run3.json
  t2_sls_run1.json
  t2_sls_run2.json
  t2_sls_run3.json
  t2_faas_run1.json
  t2_faas_run2.json
  t2_faas_run3.json
  t4_sam_run1.json  … t4_sam_run5.json
  t4_sls_run1.json  … t4_sls_run5.json
  t4_faas_run1.json … t4_faas_run5.json
```

---

## Konfigurationsparameter (in Protokollbogen eintragen)

| Parameter            | AWS SAM          | Serverless FW    | OpenFaaS (EKS)        |
|----------------------|------------------|------------------|-----------------------|
| Runtime              | provided.al2023  | provided.al2023  | Go-Container          |
| Architektur          | arm64            | arm64            | amd64                 |
| Memory               | 512 MB           | 512 MB           | n/a                   |
| Timeout              | 30 s             | 30 s             | 30 s                  |
| Stage                | prod             | prod             | n/a                   |
| Region               | eu-central-1     | eu-central-1     | eu-central-1          |
| Tracing              | PassThrough      | –                | –                     |
| k6-Version           | 0.52.0           | 0.52.0           | 0.52.0                |
| DB-Initialzustand    | 500 Einträge     | 500 Einträge     | 500 Einträge          |
