# ---- build stage ----
FROM golang:1.26-alpine AS build
WORKDIR /src

COPY . .

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
  -o /out/vehicle-service \
  ./services/vehicle-service/cmd/http

# ---- watchdog stage ----
FROM ghcr.io/openfaas/of-watchdog:0.11.2 AS watchdog

# ---- runtime stage ----
FROM alpine:3.20

COPY --from=watchdog /fwatchdog /usr/bin/fwatchdog
COPY --from=build /out/vehicle-service /usr/bin/vehicle-service

RUN printf '#!/bin/sh\n/usr/bin/vehicle-service &\nexec /usr/bin/fwatchdog\n' \
    > /usr/bin/entrypoint.sh && chmod +x /usr/bin/entrypoint.sh

ENV mode="http"
ENV upstream_url="http://127.0.0.1:8082"

EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s \
  CMD wget -qO- http://localhost:8080/healthz || exit 1

CMD ["/usr/bin/entrypoint.sh"]