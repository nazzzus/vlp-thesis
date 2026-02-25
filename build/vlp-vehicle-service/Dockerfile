FROM golang:1.23-alpine AS build
WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build \
  -o /out/vehicle-service \
  ./services/vehicle-service/cmd/http

FROM alpine:3.20

RUN apk add --no-cache curl ca-certificates \
  && curl -sSLf https://github.com/openfaas/of-watchdog/releases/download/0.10.7/of-watchdog \
    -o /usr/bin/fwatchdog \
  && chmod +x /usr/bin/fwatchdog

COPY --from=build /out/vehicle-service /usr/bin/vehicle-service

ENV mode="http"
ENV upstream_url="http://127.0.0.1:8081"
ENV fprocess="/usr/bin/vehicle-service"

EXPOSE 8080
CMD ["fwatchdog"]
