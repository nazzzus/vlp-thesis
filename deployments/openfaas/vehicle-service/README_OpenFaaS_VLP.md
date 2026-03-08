# OpenFaaS Deployment – Vehicle Listing Platform (VLP)

Dieses Dokument beschreibt vollständig das Aufsetzen, Konfigurieren, Deployen, Testen und Löschen des OpenFaaS-Deployments der VLP im Rahmen der Bachelorarbeit.

---

## Inhaltsverzeichnis

1. [Voraussetzungen](#1-voraussetzungen)
2. [Umgebungsvariablen & Exports](#2-umgebungsvariablen--exports)
3. [EKS-Cluster aufsetzen](#3-eks-cluster-aufsetzen)
4. [OpenFaaS installieren](#4-openfaas-installieren)
5. [Secrets anlegen](#5-secrets-anlegen)
6. [Image bauen & pushen](#6-image-bauen--pushen)
7. [Funktion deployen](#7-funktion-deployen)
8. [Verifizierung & Smoke-Test](#8-verifizierung--smoke-test)
9. [Konfigurationsreferenz](#9-konfigurationsreferenz)
10. [Monitoring & Debugging](#10-monitoring--debugging)
11. [Funktion aktualisieren](#11-funktion-aktualisieren)
12. [Komplettes Teardown](#12-komplettes-teardown)
13. [Bekannte Probleme & Lösungen](#13-bekannte-probleme--lösungen)

---

## 1. Voraussetzungen

### Benötigte Tools

| Tool | Version (getestet) | Installation |
|------|--------------------|--------------|
| `kubectl` | v1.35.0 | https://kubernetes.io/docs/tasks/tools/ |
| `helm` | v4.1.1 | https://helm.sh/docs/intro/install/ |
| `faas-cli` | v0.18.0 | `brew install faas-cli` |
| `aws cli` | v2.33.6 | https://aws.amazon.com/cli/ |
| `eksctl` | v0.223.0 | `brew tap weaveworks/tap && brew install eksctl` |
| `docker` | v29.1.3 | https://www.docker.com/products/docker-desktop/ |
| `k6` | v0.52.0 | `brew install k6` |

### Alle Tools auf einmal prüfen

```bash
kubectl version --client 2>/dev/null && echo "✅ kubectl" || echo "❌ kubectl fehlt"
helm version --short 2>/dev/null && echo "✅ helm" || echo "❌ helm fehlt"
faas-cli version 2>/dev/null && echo "✅ faas-cli" || echo "❌ faas-cli fehlt"
aws --version 2>/dev/null && echo "✅ aws cli" || echo "❌ aws cli fehlt"
eksctl version 2>/dev/null && echo "✅ eksctl" || echo "❌ eksctl fehlt"
docker --version 2>/dev/null && echo "✅ docker" || echo "❌ docker fehlt"
k6 version 2>/dev/null && echo "✅ k6" || echo "❌ k6 fehlt"
```

### AWS-Zugangsdaten

```bash
# Zugangsdaten konfigurieren
aws configure

# Verifizieren
aws sts get-caller-identity
```

---

## 2. Umgebungsvariablen & Exports

Einmalig in der Shell setzen – alle nachfolgenden Befehle bauen darauf auf.

```bash
# ── Cluster & Region ──────────────────────────────────────────────────────────
export AWS_REGION="eu-central-1"
export CLUSTER_NAME="vlp-cluster"

# ── GitHub Container Registry ─────────────────────────────────────────────────
export GITHUB_USER="nazzzus"
export GITHUB_PAT="<dein-github-personal-access-token>"
export IMAGE="ghcr.io/${GITHUB_USER}/vlp-vehicle-service:openfaas"

# ── MongoDB ───────────────────────────────────────────────────────────────────
export MONGO_URI="mongodb+srv://nazir_db_user:<passwort>@cluster0.cdvnklb.mongodb.net/vlp?retryWrites=true&w=majority&appName=Cluster0"
export MONGO_DB="vlp"
export MONGO_COLLECTION="vehicles"

# ── OpenFaaS Gateway (nach Deployment befüllen – siehe Schritt 4) ─────────────
export GATEWAY="http://<alb-dns-name>:8080"

# ── Funktion URL (für k6-Tests) ───────────────────────────────────────────────
export FAAS_URL="${GATEWAY}/function/vlp-vehicle-service"
```

> **Tipp:** Diese Exports in eine Datei `deployments/openfaas/.env.sh` speichern und mit `source deployments/openfaas/.env.sh` laden. Die Datei **nicht** ins Git committen (`.gitignore`).

---

## 3. EKS-Cluster aufsetzen

### Cluster erstellen

```bash
eksctl create cluster \
  --name "$CLUSTER_NAME" \
  --region "$AWS_REGION" \
  --nodegroup-name vlp-nodes \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 2 \
  --managed
```

> Dauert **15–20 Minuten**. Nicht unterbrechen.

Erfolgsmeldung: `EKS cluster "vlp-cluster" in "eu-central-1" region is ready`

### kubeconfig aktualisieren

```bash
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME"
```

### Cluster verifizieren

```bash
kubectl get nodes
# Erwartete Ausgabe: 2 Nodes mit STATUS = Ready
```

### Cluster prüfen (ob noch vorhanden)

```bash
aws eks list-clusters --region "$AWS_REGION"
```

---

## 4. OpenFaaS installieren

### Namespaces anlegen

```bash
kubectl apply -f https://raw.githubusercontent.com/openfaas/faas-netes/master/namespaces.yml
```

Erstellt: `openfaas` und `openfaas-fn`

### Helm Chart installieren

```bash
helm repo add openfaas https://openfaas.github.io/faas-netes/
helm repo update

helm install openfaas openfaas/openfaas \
  --namespace openfaas \
  --set functionNamespace=openfaas-fn \
  --set generateBasicAuth=true \
  --set serviceType=LoadBalancer
```

### Warten bis OpenFaaS bereit ist

```bash
kubectl rollout status -n openfaas deploy/gateway
# Erwartete Ausgabe: deployment "gateway" successfully rolled out
```

### Admin-Passwort und Gateway-URL ermitteln

```bash
# Passwort
export OPENFAAS_PASSWORD=$(kubectl -n openfaas get secret basic-auth \
  -o jsonpath="{.data.basic-auth-password}" | base64 --decode)
echo "Passwort: $OPENFAAS_PASSWORD"

# Gateway-URL (kann 1–2 Minuten dauern bis der LoadBalancer eine externe IP hat)
export GATEWAY=$(kubectl get svc -n openfaas gateway-external \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
export GATEWAY="http://${GATEWAY}:8080"
echo "Gateway: $GATEWAY"

# Auch FAAS_URL aktualisieren
export FAAS_URL="${GATEWAY}/function/vlp-vehicle-service"
```

### Bei OpenFaaS einloggen

```bash
faas-cli login \
  --username admin \
  --password "$OPENFAAS_PASSWORD" \
  --gateway "$GATEWAY"
```

---

## 5. Secrets anlegen

Das MongoDB-Secret wird im Namespace `openfaas-fn` als Kubernetes Secret angelegt und von OpenFaaS als Datei unter `/var/openfaas/secrets/mongodb-uri` in den Function-Pod gemountet.

```bash
kubectl create secret generic mongodb-uri \
  --from-literal=mongodb-uri="$MONGO_URI" \
  -n openfaas-fn
```

### Secret verifizieren

```bash
kubectl get secret mongodb-uri -n openfaas-fn
# NAME          TYPE     DATA   AGE
# mongodb-uri   Opaque   1      ...
```

### Secret löschen und neu anlegen (falls nötig)

```bash
kubectl delete secret mongodb-uri -n openfaas-fn
kubectl create secret generic mongodb-uri \
  --from-literal=mongodb-uri="$MONGO_URI" \
  -n openfaas-fn
```

---

## 6. Image bauen & pushen

### Bei GitHub Container Registry einloggen

```bash
echo "$GITHUB_PAT" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
# Erwartete Ausgabe: Login Succeeded
```

### Image bauen

Der Build-Kontext muss das **Repository-Root** sein, da der Go-Code unter `services/vehicle-service/` liegt.

```bash
# Aus dem Verzeichnis deployments/openfaas/vehicle-service ausführen
docker build \
  --pull \
  --platform linux/amd64 \
  -t "$IMAGE" \
  -f Dockerfile \
  ../../../
```

> `--pull` stellt sicher dass die neuesten Basis-Images verwendet werden.  
> `--platform linux/amd64` ist zwingend, da EKS-Nodes auf amd64 laufen.

### Image pushen

```bash
docker push "$IMAGE"
```

---

## 7. Funktion deployen

### stack.yml

Datei: `deployments/openfaas/vehicle-service/stack.yml`

```yaml
version: 1.0
provider:
  name: openfaas
  gateway: http://<alb-dns-name>:8080   # mit $GATEWAY befüllen

functions:
  vlp-vehicle-service:
    image: ghcr.io/nazzzus/vlp-vehicle-service:openfaas
    skip_build: true
    skip_push: true
    secrets:
      - mongodb-uri
    environment:
      fprocess: "/usr/bin/entrypoint.sh"
      PORT: "8082"
      MONGO_URI: "mongodb+srv://nazir_db_user:<passwort>@cluster0.cdvnklb.mongodb.net/vlp?retryWrites=true&w=majority&appName=Cluster0"
      MONGO_DB: "vlp"
      MONGO_COLLECTION: "vehicles"
```

> **Hinweis zur Thesis:** `MONGO_URI` steht hier aus praktischen Gründen als Klartext-Umgebungsvariable. In Produktionsumgebungen sollte ausschließlich das Kubernetes Secret verwendet und der Wert zur Laufzeit aus `/var/openfaas/secrets/mongodb-uri` gelesen werden.

### Deployen

```bash
cd deployments/openfaas/vehicle-service

faas-cli deploy -f stack.yml --gateway "$GATEWAY"
```

### Funktion neu deployen (nach Image-Update)

```bash
faas-cli deploy -f stack.yml --gateway "$GATEWAY" --update=true
```

---

## 8. Verifizierung & Smoke-Test

### Pod-Status prüfen

```bash
kubectl get pods -n openfaas-fn
# Erwartete Ausgabe:
# NAME                                   READY   STATUS    RESTARTS   AGE
# vlp-vehicle-service-xxxxxxxxxx-xxxxx   1/1     Running   0          30s
```

### Funktion beschreiben

```bash
faas-cli describe vlp-vehicle-service --gateway "$GATEWAY"
# Status: Ready
# Available Replicas: 1
```

### Healthcheck

```bash
curl -s "${FAAS_URL}/healthz"
# Erwartete Ausgabe: {"status":"ok"}
```

### Readiness-Check

```bash
curl -s "${FAAS_URL}/readyz"
# Erwartete Ausgabe: {"status":"ready"}
```

### k6 Baseline-Test (T0)

```bash
# Vom Repository-Root ausführen
k6 run --env BASE_URL="$FAAS_URL" tests/t0_baseline.js
# Alle Checks müssen ✓ grün sein
```

---

## 9. Konfigurationsreferenz

### Umgebungsvariablen der Funktion

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `fprocess` | `/usr/bin/entrypoint.sh` | Prozess den der OpenFaaS Watchdog startet |
| `PORT` | `8082` | Port auf dem der Go-Service lauscht (intern) |
| `MONGO_URI` | `mongodb+srv://...` | MongoDB-Verbindungsstring |
| `MONGO_DB` | `vlp` | MongoDB-Datenbankname |
| `MONGO_COLLECTION` | `vehicles` | MongoDB-Collection |

### Watchdog-Konfiguration (über ENV im Dockerfile/stack.yml)

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `mode` | `http` | Watchdog-Modus: Proxy zu upstream HTTP-Service |
| `upstream_url` | `http://127.0.0.1:8082` | Interner Port des Go-Services |

### Ports

| Port | Verwendung |
|------|------------|
| `8080` | OpenFaaS Watchdog (extern erreichbar, vom Gateway genutzt) |
| `8082` | Go vehicle-service (nur intern im Container) |

### Konfigurationsparameter (Thesis-Tabelle 7.1)

| Parameter | Wert |
|-----------|------|
| Laufzeitumgebung | Go-Container (amd64) |
| Speicher | n/a (Container, EKS-Node: t3.medium) |
| Timeout | 30s |
| API-Eintrittspunkt | OpenFaaS Gateway + AWS ALB |
| Datenbankanbindung | MongoDB Atlas M10 (extern) |
| Secrets-Verwaltung | Kubernetes Secret (`mongodb-uri`) |
| Deployment-Werkzeug | `faas-cli` + `helm` |
| Region | eu-central-1 |

---

## 10. Monitoring & Debugging

### Live-Logs der Funktion

```bash
kubectl logs -n openfaas-fn -l faas_function=vlp-vehicle-service -f
```

### Logs eines spezifischen Pods

```bash
# Pod-Namen anzeigen
kubectl get pods -n openfaas-fn

# Logs anzeigen
kubectl logs -n openfaas-fn <pod-name>

# Logs des vorherigen Containers (bei CrashLoop)
kubectl logs -n openfaas-fn <pod-name> --previous
```

### Events anzeigen (wichtig für Cold-Start-Messung T4)

```bash
kubectl get events -n openfaas-fn --sort-by='.lastTimestamp' | tail -20
```

### Pod details (bei Problemen)

```bash
kubectl describe pod -n openfaas-fn <pod-name>
```

### Funktion direkt im Cluster testen (ohne externen Zugriff)

```bash
kubectl run test --rm -it --image=alpine --restart=Never -- \
  wget -qO- http://gateway.openfaas.svc.cluster.local:8080/function/vlp-vehicle-service/healthz
```

### Alle OpenFaaS-Komponenten prüfen

```bash
kubectl -n openfaas get deployments -l "release=openfaas,app=openfaas"
```

---

## 11. Funktion aktualisieren

### Nur Konfiguration ändern (kein neues Image)

`stack.yml` anpassen, dann:

```bash
faas-cli deploy -f stack.yml --gateway "$GATEWAY" --update=true
```

### Neues Image bauen und deployen

```bash
# 1. Image bauen
docker build --pull --platform linux/amd64 -t "$IMAGE" -f Dockerfile ../../../

# 2. Image pushen
docker push "$IMAGE"

# 3. Funktion neu deployen
faas-cli deploy -f stack.yml --gateway "$GATEWAY" --update=true

# 4. Rollout abwarten
kubectl rollout status -n openfaas-fn deployment/vlp-vehicle-service

# 5. Verifizieren
curl -s "${FAAS_URL}/healthz"
```

---

## 12. Komplettes Teardown

### Nur Funktion entfernen (Cluster bleibt)

```bash
faas-cli remove vlp-vehicle-service --gateway "$GATEWAY"
```

### OpenFaaS komplett deinstallieren (Cluster bleibt)

```bash
helm uninstall openfaas -n openfaas
kubectl delete namespace openfaas
kubectl delete namespace openfaas-fn
```

### EKS-Cluster komplett löschen

```bash
eksctl delete cluster --name "$CLUSTER_NAME" --region "$AWS_REGION"
```

> ⚠️ **Achtung:** Dieser Befehl löscht den gesamten Cluster inklusive aller Daten. Dauert ca. 10–15 Minuten. Vorher sicherstellen dass alle Testergebnisse gesichert sind.

### Prüfen ob Cluster gelöscht wurde

```bash
aws eks list-clusters --region "$AWS_REGION"
# Erwartete Ausgabe: { "clusters": [] }
```

---

## 13. Bekannte Probleme & Lösungen

### Problem: `CrashLoopBackOff` – missing mongo configuration

**Ursache:** `MONGO_URI` ist nicht als Umgebungsvariable gesetzt, nur als Secret gemountet.  
**Lösung:** `MONGO_URI` explizit in `stack.yml` unter `environment` setzen.

```yaml
environment:
  MONGO_URI: "mongodb+srv://..."
```

---

### Problem: `provide a "function_process" or "fprocess" environmental variable`

**Ursache:** OpenFaaS Watchdog findet keinen zu startenden Prozess.  
**Lösung:** `fprocess` in `stack.yml` setzen:

```yaml
environment:
  fprocess: "/usr/bin/entrypoint.sh"
```

---

### Problem: `Error ListenAndServe: listen tcp :8080: bind: address already in use`

**Ursache:** Im `http`-Modus startet der Watchdog Port 8080 zweimal (bekanntes Verhalten bei Verwendung eines Entrypoint-Skripts). **Nicht kritisch** – der Service läuft trotzdem korrekt.  
**Erkennung:** `kubectl get pods` zeigt `1/1 Running`, `/healthz` antwortet.

---

### Problem: `denied: denied` beim `docker build` oder `docker push`

**Ursache:** Nicht bei `ghcr.io` eingeloggt.  
**Lösung:**

```bash
echo "$GITHUB_PAT" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
```

---

### Problem: Gateway-URL ist leer (`http://:8080`)

**Ursache:** LoadBalancer hat noch keine externe IP – AWS braucht 1–2 Minuten.  
**Lösung:** Warten und erneut ausführen:

```bash
kubectl get svc -n openfaas gateway-external
# Warten bis EXTERNAL-IP befüllt ist, dann:
export GATEWAY="http://$(kubectl get svc -n openfaas gateway-external \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'):8080"
```

---

### Problem: `go.work requires go >= 1.25.5 (running go 1.23.x)`

**Ursache:** `go.work` im Repository verlangt eine Go-Version die mit `golang:1.23-alpine` nicht erfüllt wird.  
**Lösung:** Im Dockerfile `golang:1.26-alpine` verwenden und `--pull` Flag beim Build nutzen:

```bash
docker build --pull --platform linux/amd64 ...
```

---

## Anhang: Vollständige Befehlssequenz (Clean Setup)

Für ein vollständiges Neu-Deployment von Grund auf:

```bash
# 0. Exports setzen
export AWS_REGION="eu-central-1"
export CLUSTER_NAME="vlp-cluster"
export GITHUB_USER="nazzzus"
export GITHUB_PAT="<token>"
export IMAGE="ghcr.io/${GITHUB_USER}/vlp-vehicle-service:openfaas"
export MONGO_URI="mongodb+srv://nazir_db_user:<passwort>@cluster0.cdvnklb.mongodb.net/vlp?retryWrites=true&w=majority&appName=Cluster0"

# 1. Cluster erstellen (~15 min)
eksctl create cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --nodegroup-name vlp-nodes --node-type t3.medium --nodes 2 --managed

# 2. kubeconfig
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME"

# 3. OpenFaaS installieren
kubectl apply -f https://raw.githubusercontent.com/openfaas/faas-netes/master/namespaces.yml
helm repo add openfaas https://openfaas.github.io/faas-netes/ && helm repo update
helm install openfaas openfaas/openfaas --namespace openfaas \
  --set functionNamespace=openfaas-fn --set generateBasicAuth=true --set serviceType=LoadBalancer
kubectl rollout status -n openfaas deploy/gateway

# 4. Gateway & Login
export OPENFAAS_PASSWORD=$(kubectl -n openfaas get secret basic-auth \
  -o jsonpath="{.data.basic-auth-password}" | base64 --decode)
export GATEWAY="http://$(kubectl get svc -n openfaas gateway-external \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'):8080"
export FAAS_URL="${GATEWAY}/function/vlp-vehicle-service"
faas-cli login --username admin --password "$OPENFAAS_PASSWORD" --gateway "$GATEWAY"

# 5. Secret
kubectl create secret generic mongodb-uri \
  --from-literal=mongodb-uri="$MONGO_URI" -n openfaas-fn

# 6. Image bauen & pushen
echo "$GITHUB_PAT" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
cd deployments/openfaas/vehicle-service
docker build --pull --platform linux/amd64 -t "$IMAGE" -f Dockerfile ../../../
docker push "$IMAGE"

# 7. Deployen
faas-cli deploy -f stack.yml --gateway "$GATEWAY"

# 8. Verifizieren
kubectl get pods -n openfaas-fn
curl -s "${FAAS_URL}/healthz"
k6 run --env BASE_URL="$FAAS_URL" ../../../tests/t0_baseline.js
```