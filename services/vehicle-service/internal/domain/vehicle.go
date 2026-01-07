package domain

import "time"

type Vehicle struct {
	ID        string    `json:"id" bson:"_id"`
	Title     string    `json:"title" bson:"title"`
	Make      string    `json:"make" bson:"make"`
	Model     string    `json:"model" bson:"model"`
	Year      int       `json:"year" bson:"year"`
	Price     any       `json:"price" bson:"price"`
	CreatedAt time.Time `json:"createdAt" bson:"createdAt"`
}
