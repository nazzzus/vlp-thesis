# API Example Requests – Vehicle Listing Platform (VLP)

This document lists example HTTP requests for all available API endpoints
of the Vehicle Listing Platform (VLP).

Base URL (local):
http://localhost:8081

---

## 1. Health Check

### Endpoint
GET /healthz

### Description
Liveness probe. Indicates whether the service is running.

### Example
```bash
curl -i http://localhost:8081/healthz

Response: 
{"status":"ok"}
```

---

## 2. Readiness Check

### Endpoint
GET /readyz

### Description
Readiness probe. Indicates whether the service is ready to receive traffic
(e.g. database connection available).

### Example
```bash
curl -i http://localhost:8081/readyz

Response: 
{"status":"ready"}
```
---

## 3. List Vehicles

### Endpoint
GET /vehicles

### Description
Returns a list of vehicle listings.
Supports an optional limit parameter.

### Query Parameters
- limit (optional): maximum number of vehicles returned (default: 50)

### Example
```bash
curl -i "http://localhost:8081/vehicles?limit=50"

Response: 
[
  {
    "id": "747eec07-9406-40f4-8fe4-d629feeee98a",
    "title": "MAN Lion's City",
    "make": "MAN",
    "model": "A78",
    "year": 2011,
    "price": 13000,
    "fuel": "Diesel",
    "mileage": 680000,
    "description": "Gepflegter Linienbus",
    "createdAt": "2026-01-05T18:29:35Z"
  }
]
```
---
## 4. List Vehicles

### Endpoint
GET /vehicles/{id}

### Description
Returns a single vehicle listing by its unique identifier.

### Example
```bash
curl -i http://localhost:8081/vehicles/747eec07-9406-40f4-8fe4-d629feeee98a

Response: 
[
  {
    "id": "747eec07-9406-40f4-8fe4-d629feeee98a",
    "title": "MAN Lion's City",
    "make": "MAN",
    "model": "A78",
    "year": 2011,
    "price": 13000,
    "fuel": "Diesel",
    "mileage": 680000,
    "description": "Gepflegter Linienbus",
    "createdAt": "2026-01-05T18:29:35Z"
  }
]
```
---
## 5. Create Vehicle

### Endpoint
POST /vehicles

### Description
Creates a new vehicle listing.

### Request Body (JSON)
```bash
{
  "title": "MAN A78 Linienbus",
  "make": "MAN",
  "model": "A78",
  "year": 2011,
  "price": 13000,
  "fuel": "Diesel",
  "mileage": 680000,
  "description": "Gepflegter Linienbus, voll funktionsfähig"
}
```
### Example
```bash
curl -i -X POST http://localhost:8081/vehicles \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MAN A78 Linienbus",
    "make": "MAN",
    "model": "A78",
    "year": 2011,
    "price": 13000,
    "fuel": "Diesel",
    "mileage": 680000,
    "description": "Gepflegter Linienbus, voll funktionsfähig"
  }'
```
---
---
## 6. Delete Vehicle

### Endpoint
DELETE /vehicles/{id}

### Description
Deletes a vehicle listing by its ID.

### Example
```bash
curl -i -X DELETE http://localhost:8081/vehicles/747eec07-9406-40f4-8fe4-d629feeee98a
```
---
