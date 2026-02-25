package config

import (
	"fmt"
	"os"
)

type Config struct {
	ServiceName     string
	HTTPPort        string
	MongoURI        string
	MongoDatabase   string
	MongoCollection string
}

func Load() (Config, error) {
	cfg := Config{
		ServiceName:     getenv("SERVICE_NAME", "vehicle-service"),
		HTTPPort:        getenvFirst([]string{"PORT", "HTTP_PORT"}, "8081"),
		MongoURI:        getenv("MONGO_URI", ""),
		MongoDatabase:   getenv("MONGO_DB", "vlp"),
		MongoCollection: getenv("MONGO_COLLECTION", "vehicles"),
	}

	if cfg.MongoURI == "" || cfg.MongoDatabase == "" || cfg.MongoCollection == "" {
		return Config{}, fmt.Errorf("missing mongo configuration (MONGO_URI/MONGO_DB/MONGO_COLLECTION)")
	}

	return cfg, nil
}

func getenv(key, def string) string {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	return v
}

func getenvFirst(keys []string, def string) string {
	for _, k := range keys {
		if v := os.Getenv(k); v != "" {
			return v
		}
	}
	return def
}
