## Vehicle Listing Platform (VLP)

### Deutsch

Die Vehicle Listing Platform (VLP) ist eine cloud-native Referenzanwendung zur empirischen Evaluation von Serverless-Frameworks.
Sie stellt eine bewusst schlank gehaltene REST-API zur Verwaltung von Fahrzeuginseraten bereit und dient als reproduzierbare
Workload-Basis für Performance-, Kosten- und Entwicklungsaufwand-Vergleiche im Rahmen einer Bachelorarbeit.

Der Funktionsumfang ist absichtlich begrenzt, um framework-spezifische Effekte isoliert messen und unterschiedliche
Deployment-Modelle unter identischen Bedingungen vergleichen zu können.

---

### English

The Vehicle Listing Platform (VLP) is a cloud-native reference application designed for the empirical evaluation of
serverless computing frameworks. It provides a deliberately minimal RESTful API for managing vehicle listings and serves
as a reproducible benchmark workload for performance, cost, and development-effort comparisons in the context of a
bachelor’s thesis.

The scope of the application is intentionally limited in order to isolate framework-specific effects and ensure
comparability across different deployment models.

---

## Local Development / Lokale Entwicklung

### Prerequisites / Voraussetzungen
- Docker including Docker Compose
- Go (version according to `go.work`)

### Startup / Start

```bash
docker compose up -d
cd services/vehicle-service
go run ./cmd/http
```

The service is exposed on port 8081 by default.
Der Service ist standardmäßig unter Port 8081 erreichbar.

### API Overview / API-Übersicht

The following endpoints constitute the benchmark workload of the application.
Die folgenden Endpunkte bilden die Benchmark-Workload der Anwendung.

- GET /healthz
Liveness check indicating whether the service is running.
Liveness-Check zur Prüfung, ob der Service läuft.

- GET /readyz
Readiness check indicating whether the service is ready to receive requests
(e.g. database connection available).
Readiness-Check zur Prüfung der Betriebsbereitschaft (z. B. verfügbare Datenbankverbindung).

- GET /vehicles
Returns a list of vehicle listings.
Gibt eine Liste von Fahrzeuginseraten zurück.

- GET /vehicles/{id}
Returns a single vehicle listing by its identifier.
Gibt ein einzelnes Inserat anhand der ID zurück.

- POST /vehicles
Creates a new vehicle listing.
Legt ein neues Inserat an.

- DELETE /vehicles/{id}
Deletes an existing vehicle listing.
Löscht ein bestehendes Inserat.

Detailed example requests are documented in
API_EXAMPLES.md
.

Detaillierte Beispielanfragen sind in
API_EXAMPLES.md
 dokumentiert.

### Purpose and Scope / Zweck und Abgrenzung

The VLP is not intended to be a feature-complete production system. It is designed as a controlled experimental
environment for the comparative analysis of serverless frameworks under identical functional and workload conditions.

The implementation focuses on:
- clear separation of concerns,
- cloud-native design principles (e.g. health and readiness probes),
- reproducibility of experiments,
- minimal configuration and integration effort.

Die VLP ist nicht als vollumfängliches Produktivsystem konzipiert, sondern dient als kontrollierte Experimentierumgebung
zur vergleichenden Untersuchung von Serverless-Frameworks unter gleichen funktionalen Anforderungen und Testbedingungen.