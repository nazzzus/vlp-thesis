import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getVehicleById } from "../api/vehicles.js";

function formatEuro(value) {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return "Preis auf Anfrage";
    return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(n);
}

function Badge({ children }) {
    return (
        <span className="rounded-full border border-zinc-800 bg-zinc-950 px-2 py-1 text-xs text-zinc-200">
      {children}
    </span>
    );
}

export default function VehicleDetail() {
    const { id } = useParams();
    const [v, setV] = useState(null);
    const [err, setErr] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                setLoading(true);
                setErr("");
                const data = await getVehicleById(id);
                setV(data);
            } catch (e) {
                setErr(e?.message ?? "Failed");
            } finally {
                setLoading(false);
            }
        })();
    }, [id]);

    const title = useMemo(() => {
        if (!v) return "";
        return v.title ?? [v.make, v.model].filter(Boolean).join(" ") ?? "Inserat";
    }, [v]);

    return (
        <div className="bg-zinc-950 text-zinc-100">
            <div className="mx-auto w-full max-w-screen-2xl px-4 py-6">
                <Link to="/listings" className="text-sm text-zinc-400 hover:text-zinc-100">
                    ← zurück
                </Link>

                {loading && <div className="mt-4 text-sm text-zinc-400">Lade…</div>}
                {err && (
                    <div className="mt-4 rounded-2xl border border-red-900/50 bg-red-950/30 p-4 text-sm text-red-200">
                        {err}
                    </div>
                )}

                {v && (
                    <div className="mt-4 grid gap-4 lg:grid-cols-3">
                        <section className="lg:col-span-2 space-y-4">
                            <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
                                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                                    <div className="min-w-0">
                                        <h1 className="truncate text-2xl font-semibold tracking-tight">{title}</h1>
                                        <p className="mt-1 text-sm text-zinc-400">
                                            {[v.make, v.model, v.year].filter(Boolean).join(" · ") || "—"}
                                        </p>

                                        <div className="mt-3 flex flex-wrap gap-2">
                                            <Badge>Baujahr: {v.year ?? "—"}</Badge>
                                            {v.mileage != null && (
                                                <Badge>
                                                    KM: {new Intl.NumberFormat("de-DE").format(Number(v.mileage))} km
                                                </Badge>
                                            )}
                                            {v.fuel && <Badge>{v.fuel}</Badge>}
                                        </div>
                                    </div>

                                    <div className="shrink-0 rounded-2xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-right">
                                        <div className="text-lg font-semibold">{formatEuro(v.price)}</div>
                                        {Number(v.price) > 0 && (
                                            <div className="text-xs text-zinc-500">
                                                {v.vatIncluded ? "inkl. MwSt." : "zzgl. MwSt."}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                                    <div className="sm:col-span-2 grid gap-3">
                                        <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-3">
                                            <div className="text-xs text-zinc-500">ID</div>
                                            <div className="break-all font-mono text-xs text-zinc-200">
                                                {v.id ?? v._id ?? "—"}
                                            </div>
                                        </div>

                                        <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-3">
                                            <div className="text-xs text-zinc-500">Beschreibung</div>
                                            <div className="mt-1 text-sm text-zinc-300">
                                                {v.description?.trim() ? v.description : "—"}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        <aside className="space-y-4">
                            <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
                                <div className="text-sm font-semibold">Technische Daten</div>
                                <div className="mt-3 space-y-2 text-sm text-zinc-300">
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="text-zinc-500">Marke</span>
                                        <span>{v.make ?? "—"}</span>
                                    </div>
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="text-zinc-500">Modell</span>
                                        <span>{v.model ?? "—"}</span>
                                    </div>
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="text-zinc-500">Baujahr</span>
                                        <span>{v.year ?? "—"}</span>
                                    </div>
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="text-zinc-500">KM</span>
                                        <span>
                      {v.mileage != null
                          ? `${new Intl.NumberFormat("de-DE").format(Number(v.mileage))} km`
                          : "—"}
                    </span>
                                    </div>
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="text-zinc-500">Kraftstoff</span>
                                        <span>{v.fuel ?? "—"}</span>
                                    </div>
                                </div>
                            </div>
                            <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-5">
                                <div className="text-sm font-semibold">Kontakt</div>
                                <p className="mt-2 text-sm text-zinc-400">Demo UI – hier später Kontakt-CTA.</p>
                                <button
                                    className="mt-3 w-full rounded-xl bg-zinc-100 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-white">
                                    Anfrage senden
                                </button>
                            </div>
                        </aside>
                    </div>
                )}
            </div>
        </div>
    );
}
