package http

type CreateVehicleRequest struct {
	Title       string `json:"title"`
	Make        string `json:"make"`
	Model       string `json:"model"`
	Year        int    `json:"year"`
	Price       *int64 `json:"price,omitempty"`
	Fuel        string `json:"fuel,omitempty"`
	Mileage     int    `json:"mileage,omitempty"`
	Description string `json:"description,omitempty"`
}
