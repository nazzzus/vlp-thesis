package service

import (
	"context"
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
