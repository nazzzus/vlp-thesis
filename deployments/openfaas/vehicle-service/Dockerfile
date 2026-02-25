# ---- build stage ----
FROM golang:1.25.5-alpine AS build
WORKDIR /src

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build \
  -o /out/vehicle-service \
  ./services/vehicle-service/cmd/http

# ---- watchdog stage (liefert /fwatchdog passend zur Architektur) ----
FROM ghcr.io/openfaas/of-watchdog:0.11.2 AS watchdog

# ---- runtime stage ----
FROM alpine:3.20

# fwatchdog aus dem offiziellen Image kopieren (kein Download nötig)
COPY --from=watchdog /fwatchdog /usr/bin/fwatchdog

COPY --from=build /out/vehicle-service /usr/bin/vehicle-service

ENV mode="http"
ENV upstream_url="http://127.0.0.1:8081"
ENV fprocess="/usr/bin/vehicle-service"

EXPOSE 8080
CMD ["/usr/bin/fwatchdog"]
