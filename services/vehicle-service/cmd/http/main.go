package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

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

	go func() {
		log.Printf("listening on :%s", cfg.HTTPPort)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server error: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	_ = srv.Shutdown(shutdownCtx)
	log.Println("shutdown complete")
}
