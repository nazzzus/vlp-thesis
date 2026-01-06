## Vehicle Listing Platform (VLP)

Cloud-native reference application for empirical evaluation of serverless frameworks.

### Local development
```bash
docker compose up -d
cd services/vehicle-service
go run ./cmd/http


Endpoints
- GET /healthz

- GET /readyz

- POST /vehicles