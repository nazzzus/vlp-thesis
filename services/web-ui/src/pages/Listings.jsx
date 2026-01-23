import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

function formatEuro(value) {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return "Preis auf Anfrage";
    return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(n);
}

function formatInt(value, suffix = "") {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return "—";
    return `${new Intl.NumberFormat("de-DE").format(n)}${suffix}`;
}

function safeString(v) {
    return (v ?? "").toString().trim();
}

function parseDateMs(d) {
    const t = new Date(d ?? 0).getTime();
    return Number.isFinite(t) ? t : 0;
}

function Badge({ children }) {
    return (
        <span className="rounded-full border border-zinc-800 bg-zinc-950 px-2 py-1 text-xs text-zinc-200">
      {children}
    </span>
    );
}

export default function Listings() {
    const [items, setItems] = useState([]);
    const [query, setQuery] = useState("");
    const [sort, setSort] = useState("newest"); // newest | priceAsc | priceDesc | yearDesc
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let cancelled = false;

        async function load() {
            setLoading(true);
            setError("");
            try {
                const base = import.meta.env.VITE_API_BASE_URL;
                if (!base) throw new Error("VITE_API_BASE_URL is not set");

                const res = await fetch(`${base}/vehicles?limit=500`);
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const data = await res.json();

                const arr = Array.isArray(data) ? data : (data.items ?? []);
                if (!cancelled) setItems(arr);
            } catch (e) {
                if (!cancelled) setError("Listings konnten nicht geladen werden. Bitte Backend/API prüfen.");
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => {
            cancelled = true;
        };
    }, []);

    const filtered = useMemo(() => {
        const q = query.toLowerCase().trim();

        const base = items.filter((x) => {
            if (!q) return true;

            const title = safeString(x.title).toLowerCase();
            const brand = safeString(x.brand).toLowerCase();
            const model = safeString(x.model).toLowerCase();
            const year = safeString(x.year).toLowerCase();

            return title.includes(q) || brand.includes(q) || model.includes(q) || year.includes(q);
        });

        const sorted = [...base].sort((a, b) => {
            const pa = Number(a.price ?? 0);
            const pb = Number(b.price ?? 0);
            const ya = Number(a.year ?? 0);
            const yb = Number(b.year ?? 0);

            switch (sort) {
                case "priceAsc":
                    return pa - pb;
                case "priceDesc":
                    return pb - pa;
                case "yearDesc":
                    return yb - ya;
                case "newest":
                default:
                    return parseDateMs(b.createdAt) - parseDateMs(a.createdAt);
            }
        });

        return sorted;
    }, [items, query, sort]);

    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-100">
            <header className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
                <div className="mx-auto flex w-full max-w-screen-2xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-baseline gap-3">
                        <h1 className="text-xl font-semibold tracking-tight">Inserate</h1>
                        <span className="text-sm text-zinc-400">{filtered.length} Einträge</span>
                    </div>

                    <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
                        <div className="relative w-full sm:w-80">
                            <input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Suchen: Marke, Modell, Titel, Jahr…"
                                className="w-full rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-600"
                            />
                        </div>

                        <select
                            value={sort}
                            onChange={(e) => setSort(e.target.value)}
                            className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-zinc-600"
                        >
                            <option value="newest">Sortierung: Neueste</option>
                            <option value="yearDesc">Sortierung: Baujahr ↓</option>
                            <option value="priceAsc">Sortierung: Preis ↑</option>
                            <option value="priceDesc">Sortierung: Preis ↓</option>
                        </select>
                    </div>
                </div>
            </header>

            <main className="mx-auto w-full max-w-screen-2xl px-4 py-6">
                {loading && (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
                        {Array.from({length: 6}).map((_, i) => (
                            <div key={i} className="rounded-2xl border border-zinc-800 bg-zinc-900 p-4">
                                <div className="h-5 w-2/3 animate-pulse rounded bg-zinc-800"/>
                                <div className="mt-3 h-4 w-1/2 animate-pulse rounded bg-zinc-800"/>
                                <div className="mt-6 h-6 w-1/3 animate-pulse rounded bg-zinc-800"/>
                                <div className="mt-4 h-9 w-full animate-pulse rounded-xl bg-zinc-800"/>
                            </div>
                        ))}
                    </div>
                )}

                {!loading && error && (
                    <div className="rounded-2xl border border-red-900/50 bg-red-950/30 p-4 text-sm text-red-200">
                        {error}
                    </div>
                )}

                {!loading && !error && filtered.length === 0 && (
                    <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6">
                        <h2 className="text-base font-semibold">Keine Inserate gefunden</h2>
                        <p className="mt-1 text-sm text-zinc-400">Passe die Suche an oder lege ein neues Inserat an.</p>
                    </div>
                )}

                {!loading && !error && filtered.length > 0 && (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
                        {filtered.map((x) => {
                            const id = x.id ?? x._id;
                            const title =
                                x.title || `${safeString(x.brand)} ${safeString(x.model)}`.trim() || "Inserat";

                            const meta = [x.brand, x.model, x.year].filter(Boolean).join(" · ");

                            const priceLabel = formatEuro(x.price);
                            const vatLabel = x.vatIncluded ? "inkl. MwSt." : "zzgl. MwSt.";

                            return (
                                <article
                                    key={id ?? `${title}-${x.year}-${x.price}`}
                                    className="group flex h-full flex-col overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900 transition hover:border-zinc-700 hover:bg-zinc-900/70"
                                >
                                    <div className="p-4">
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="min-w-0">
                                                <h3 className="truncate text-base font-semibold leading-snug">{title}</h3>
                                                <p className="mt-1 text-sm text-zinc-400">{meta || "—"}</p>
                                            </div>

                                            <div className="shrink-0 text-right">
                                                <div className="text-lg font-semibold">{priceLabel}</div>
                                                <div
                                                    className="text-xs text-zinc-500">{priceLabel === "Preis auf Anfrage" ? "" : vatLabel}</div>
                                            </div>
                                        </div>

                                        <div className="mt-4 flex flex-wrap gap-2">
                                            <Badge>Baujahr: {x.year ?? "—"}</Badge>
                                            <Badge>KM: {formatInt(x.mileage, " km")}</Badge>
                                            {x.fuel && <Badge>{x.fuel}</Badge>}
                                        </div>
                                    </div>

                                    <div className="mt-auto border-t border-zinc-800 p-4">
                                        <Link
                                            to={`/listings/${id}`}
                                            className="inline-flex w-full items-center justify-center rounded-xl bg-zinc-100 px-3 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-white"
                                        >
                                            Details ansehen
                                        </Link>
                                    </div>
                                </article>
                            );
                        })}
                    </div>
                )}

                <footer className="mt-10 border-t border-zinc-800 pt-4 text-xs text-zinc-500">
                    VLP Demo UI — Frontend ist nicht Bestandteil der Messungen.
                </footer>
            </main>
        </div>
    );
}
