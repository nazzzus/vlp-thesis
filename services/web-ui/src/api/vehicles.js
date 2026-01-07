import { apiFetch } from "./client";

export async function getVehicles() {
    const data = await apiFetch("/vehicles");
    return Array.isArray(data) ? data : (data?.items ?? []);
}

export async function getVehicleById(id) {
    return apiFetch(`/vehicles/${id}`);
}

export async function createVehicle(payload) {
    return apiFetch("/vehicles", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export async function updateVehicle(id, payload) {
    return apiFetch(`/vehicles/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
    });
}

export async function patchVehicle(id, payload) {
    return apiFetch(`/vehicles/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    });
}

export async function deleteVehicle(id) {
    return apiFetch(`/vehicles/${id}`, {
        method: "DELETE",
    });
}

