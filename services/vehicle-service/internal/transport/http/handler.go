package http

import (
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/nazzzus/vlp/services/vehicle-service/internal/domain"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/repository"
	"github.com/nazzzus/vlp/services/vehicle-service/internal/service"

	"go.mongodb.org/mongo-driver/mongo"
)

type Handler struct {
	svc  *service.VehicleService
	repo repository.VehicleRepository
}

func NewHandler(svc *service.VehicleService, repo repository.VehicleRepository) *Handler {
	return &Handler{svc: svc, repo: repo}
}

func (h *Handler) Healthz(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
}

func (h *Handler) Readyz(w http.ResponseWriter, r *http.Request) {
	// kurze Timeout-Readiness, damit es cloud-native ist
	ctx := r.Context()
	_ = ctx

	// Ping optional mit Timeout
	type result struct {
		err error
	}
	ch := make(chan result, 1)

	go func() {
		ch <- result{err: h.repo.Ping(r.Context())}
	}()

	select {
	case res := <-ch:
		if res.err != nil {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"status": "not-ready", "error": res.err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"status": "ready"})
	case <-time.After(2 * time.Second):
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{"status": "not-ready", "error": "mongo ping timeout"})
	}
}

func (h *Handler) CreateVehicle(w http.ResponseWriter, r *http.Request) {
	var req CreateVehicleRequest

	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()

	if err := dec.Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json"})
		return
	}

	// Optional, aber sauber: keine "zweiten JSON-Objekte" im Body erlauben
	if dec.More() {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "invalid json"})
		return
	}

	// Validation (Request-Level)
	if req.Title == "" || req.Make == "" || req.Model == "" {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "title, make and model are required"})
		return
	}
	if len(req.Description) > 1000 {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "description must be <= 1000 characters"})
		return
	}
	if req.Mileage < 0 || req.Mileage > 2_000_000 {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "mileage out of range"})
		return
	}
	if req.Year < 1950 || req.Year > time.Now().Year()+1 {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "year out of range"})
		return
	}
	if req.Price != nil && *req.Price < 0 {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "price must be >= 0"})
		return
	}

	in := domain.Vehicle{
		Title:       req.Title,
		Make:        req.Make,
		Model:       req.Model,
		Year:        req.Year,
		Price:       req.Price,
		Fuel:        req.Fuel,
		Mileage:     req.Mileage,
		Description: req.Description,
	}

	out, err := h.svc.Create(r.Context(), in)
	if err != nil {
		if errors.Is(err, domain.ErrValidation) {
			writeJSON(w, http.StatusBadRequest, map[string]any{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusInternalServerError, map[string]any{"error": err.Error()})
		return
	}

	writeJSON(w, http.StatusCreated, out)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func (h *Handler) ListVehicles(w http.ResponseWriter, r *http.Request) {
	items, err := h.svc.List(r.Context(), 50)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]any{"error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, items)
}

func (h *Handler) GetVehicle(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	v, err := h.svc.GetByID(r.Context(), id)
	if err != nil {
		writeJSON(w, http.StatusNotFound, map[string]any{"error": "not found"})
		return
	}
	writeJSON(w, http.StatusOK, v)
}

func (h *Handler) DeleteVehicle(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "missing id"})
		return
	}

	err := h.svc.DeleteVehicle(r.Context(), id)
	if err != nil {
		if errors.Is(err, mongo.ErrNoDocuments) {
			writeJSON(w, http.StatusNotFound, map[string]any{"error": "not found"})
			return
		}
		writeJSON(w, http.StatusInternalServerError, map[string]any{"error": err.Error()})
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
