package main

import (
	"context"
	"time"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/awslabs/aws-lambda-go-api-proxy/httpadapter"

	"github.com/nazzzus/vlp/services/vehicle-service/internal/config"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/observability"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/repository"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/service"
	transport "github.com/nazzzus/vlp/services/vehicle-service/internal/transport/http"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		panic(err)
	}

	log := observability.New(cfg.ServiceName)

	// Wichtig: Initialisierung OUTSIDE Handler (wird bei warm starts wiederverwendet)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	repo, err := repository.NewMongoVehicleRepository(ctx, cfg.MongoURI, cfg.MongoDatabase, cfg.MongoCollection)
	if err != nil {
		log.Fatalf("mongo init failed: %v", err)
	}

	svc := service.NewVehicleService(repo)
	h := transport.NewHandler(svc, repo)
	handler := transport.Routes(h)

	adapter := httpadapter.New(handler)

	lambda.Start(adapter.ProxyWithContext)
}
