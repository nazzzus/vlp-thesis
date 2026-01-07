const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8081";

export async function apiFetch(path, options = {}) {
    const res = await fetch(`${BASE_URL}${path}`, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API error ${res.status}: ${text}`);
    }

    // 204 No Content absichern
    if (res.status === 204) return null;

    return res.json();
}