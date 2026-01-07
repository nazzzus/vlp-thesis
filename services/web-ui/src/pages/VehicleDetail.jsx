import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getVehicleById} from "../api/vehicles.js";

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

    return (
        <div className="space-y-4">
            <Link to={`/listings`} className="text-sm text-zinc-600 hover:text-zinc-900">← zurück</Link>

            {loading && <div className="text-sm text-zinc-600">Lade…</div>}
            {err && <div className="text-sm text-red-600">{err}</div>}

            {v && (
                <div className="grid gap-4 lg:grid-cols-3">
                    <div className="lg:col-span-2 space-y-4">
                        <div className="aspect-[16/9] rounded-2xl bg-zinc-200" />
                        <div className="rounded-2xl border bg-white p-4 shadow-sm">
                            <div className="text-lg font-semibold">{v.title ?? "Inserat"}</div>
                            <div className="mt-1 text-sm text-zinc-600">{v.make} {v.model} • {v.year}</div>
                            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                                <div className="rounded-xl bg-zinc-50 p-3">
                                    <div className="text-xs text-zinc-500">ID</div>
                                    <div className="break-all font-mono text-xs">{v.id}</div>
                                </div>
                                <div className="rounded-xl bg-zinc-50 p-3">
                                    <div className="text-xs text-zinc-500">Preis</div>
                                    <div className="font-semibold">{v.price}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <aside className="space-y-4">
                        <div className="rounded-2xl border bg-white p-4 shadow-sm">
                            <div className="text-sm font-semibold">Kontakt</div>
                            <div className="mt-2 text-sm text-zinc-600">
                                Demo UI – hier später Kontakt-CTA.
                            </div>
                            <button className="mt-3 w-full rounded-xl bg-zinc-900 px-4 py-2 text-sm font-semibold text-white hover:bg-zinc-800">
                                Anfrage senden
                            </button>
                        </div>
                    </aside>
                </div>
            )}
        </div>
    );
}
