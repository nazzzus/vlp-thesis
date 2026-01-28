package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/joho/godotenv"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/config"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/observability"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/repository"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/service"
	transport "github.com/nazzzus/vlp/services/vehicle-service/internal/transport/http"
)

func main() {
	//// 1) Erst .env laden
	////   Logger mit festem Prefix erzeugen
	bootstrapLog := observability.New("vehicle-service")
	if err := godotenv.Load(); err != nil {
		bootstrapLog.Println("no .env file found, relying on environment variables")
	}

	//// 2) Config laden
	cfg, err := config.Load()
	if err != nil {
		bootstrapLog.Fatalf("config load failed: %v", err)
	}

	//// 3) Ab hier: Logger mit echtem ServiceName
	log := observability.New(cfg.ServiceName)

	//// 4) Dependencies bauen
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	repo, err := repository.NewMongoVehicleRepository(ctx, cfg.MongoURI, cfg.MongoDatabase, cfg.MongoCollection)
	if err != nil {
		log.Fatalf("mongo init failed: %v", err)
	}

	svc := service.NewVehicleService(repo)
	h := transport.NewHandler(svc, repo)
	handler := transport.Routes(h)

	srv := &http.Server{
		Addr:              ":" + cfg.HTTPPort,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
	}

	//// 5) Server starten
	go func() {
		log.Printf("listening on :%s", cfg.HTTPPort)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	//// 6) Graceful shutdown
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	_ = srv.Shutdown(shutdownCtx)
	log.Println("shutdown complete")
}
