package domain

import "time"

type Vehicle struct {
	ID          string    `json:"id" bson:"_id"`
	Title       string    `json:"title" bson:"title"`
	Make        string    `json:"make" bson:"make"`
	Model       string    `json:"model" bson:"model"`
	Year        int       `json:"year" bson:"year"`
	Price       *int64    `json:"price,omitempty" bson:"price,omitempty"`
	Fuel        string    `json:"fuel,omitempty" bson:"fuel,omitempty"`
	Mileage     int       `json:"mileage,omitempty" bson:"mileage,omitempty"`
	Description string    `json:"description,omitempty" bson:"description,omitempty"`
	CreatedAt   time.Time `json:"createdAt" bson:"createdAt"`
}
