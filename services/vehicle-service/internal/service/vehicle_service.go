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
