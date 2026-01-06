package repository

import (
	"context"
	"fmt"
	"time"

	"github.com/nazzzus/vlp/services/vehicle-service/internal/domain"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type VehicleRepository interface {
	Ping(ctx context.Context) error
	Create(ctx context.Context, v domain.Vehicle) (domain.Vehicle, error)
}

type MongoVehicleRepository struct {
	client     *mongo.Client
	collection *mongo.Collection
}

func NewMongoVehicleRepository(ctx context.Context, uri, db, coll string) (*MongoVehicleRepository, error) {
	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		return nil, fmt.Errorf("mongo connect: %w", err)
	}

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := client.Ping(pingCtx, nil); err != nil {
		return nil, fmt.Errorf("mongo ping: %w", err)
	}

	c := client.Database(db).Collection(coll)
	return &MongoVehicleRepository{client: client, collection: c}, nil
}

func (r *MongoVehicleRepository) Ping(ctx context.Context) error {
	return r.client.Ping(ctx, nil)
}

func (r *MongoVehicleRepository) Create(ctx context.Context, v domain.Vehicle) (domain.Vehicle, error) {
	_, err := r.collection.InsertOne(ctx, v)
	if err != nil {
		return domain.Vehicle{}, fmt.Errorf("insert vehicle: %w", err)
	}
	return v, nil
}

// Optional: nur um zu zeigen, dass DB wirklich erreichbar ist
func (r *MongoVehicleRepository) Count(ctx context.Context) (int64, error) {
	return r.collection.CountDocuments(ctx, bson.M{})
}
