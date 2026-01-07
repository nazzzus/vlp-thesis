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
	FindByID(ctx context.Context, id string) (domain.Vehicle, error)
	List(ctx context.Context, limit int64) ([]domain.Vehicle, error)
	DeleteByID(ctx context.Context, id string) error
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

func (r *MongoVehicleRepository) FindByID(ctx context.Context, id string) (domain.Vehicle, error) {
	var v domain.Vehicle
	err := r.collection.FindOne(ctx, bson.M{"_id": id}).Decode(&v)
	if err != nil {
		return domain.Vehicle{}, err
	}
	return v, nil
}

func (r *MongoVehicleRepository) List(ctx context.Context, limit int64) ([]domain.Vehicle, error) {
	opts := options.Find()
	if limit <= 0 || limit > 200 {
		limit = 50
	}
	opts.SetLimit(limit)
	opts.SetSort(bson.D{{Key: "createdAt", Value: -1}})

	cur, err := r.collection.Find(ctx, bson.M{}, opts)
	if err != nil {
		return nil, err
	}
	defer cur.Close(ctx)

	var out []domain.Vehicle
	if err := cur.All(ctx, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func (r *MongoVehicleRepository) DeleteByID(ctx context.Context, id string) error {
	res, err := r.collection.DeleteOne(ctx, bson.M{"_id": id})
	if err != nil {
		return err
	}
	if res.DeletedCount == 0 {
		return mongo.ErrNoDocuments
	}
	return nil
}
