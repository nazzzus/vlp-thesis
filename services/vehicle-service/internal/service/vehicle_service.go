package service

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/domain"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/repository"
)

type VehicleService struct {
	repo repository.VehicleRepository
}

func NewVehicleService(repo repository.VehicleRepository) *VehicleService {
	return &VehicleService{repo: repo}
}

func (s *VehicleService) Create(ctx context.Context, in domain.Vehicle) (domain.Vehicle, error) {
	// Domain-Validation (Defense-in-depth)
	in.Title = strings.TrimSpace(in.Title)
	in.Make = strings.TrimSpace(in.Make)
	in.Model = strings.TrimSpace(in.Model)
	in.Fuel = strings.TrimSpace(in.Fuel)
	in.Description = strings.TrimSpace(in.Description)

	if in.Title == "" || in.Make == "" || in.Model == "" {
		return domain.Vehicle{}, fmt.Errorf("%w: title, make and model are required", domain.ErrValidation)
	}
	if len(in.Description) > 1000 {
		return domain.Vehicle{}, fmt.Errorf("%w: description must be <= 1000 characters", domain.ErrValidation)
	}
	if in.Mileage < 0 || in.Mileage > 2_000_000 {
		return domain.Vehicle{}, fmt.Errorf("%w: mileage out of range", domain.ErrValidation)
	}
	if in.Year < 1950 || in.Year > time.Now().Year()+1 {
		return domain.Vehicle{}, fmt.Errorf("%w: year out of range", domain.ErrValidation)
	}
	if in.Price != nil && *in.Price < 0 {
		return domain.Vehicle{}, fmt.Errorf("%w: price must be >= 0", domain.ErrValidation)
	}

	in.ID = uuid.NewString()
	in.CreatedAt = time.Now().UTC()

	return s.repo.Create(ctx, in)
}

func (s *VehicleService) GetByID(ctx context.Context, id string) (domain.Vehicle, error) {
	return s.repo.FindByID(ctx, id)
}

func (s *VehicleService) List(ctx context.Context, limit int64) ([]domain.Vehicle, error) {
	return s.repo.List(ctx, limit)
}

func (s *VehicleService) DeleteVehicle(ctx context.Context, id string) error {
	return s.repo.DeleteByID(ctx, id)
}
