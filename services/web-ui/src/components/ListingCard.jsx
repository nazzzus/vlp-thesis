import { Link } from "react-router-dom";

/**
 * Formatiert Preise korrekt für DE (EUR)
 */
function moneyEUR(value) {
    if (typeof value !== "number") return "Auf Anfrage";
    return new Intl.NumberFormat("de-DE", {
        style: "currency",
        currency: "EUR",
    }).format(value);
}

export default function ListingCard({ vehicle }) {
    // Schutz gegen undefined → verhindert deinen aktuellen Crash
    if (!vehicle) return null;

    const title = vehicle.title ?? "(ohne Titel)";
    const make = vehicle.make ?? "";
    const model = vehicle.model ?? "";
    const year = vehicle.year ?? "";
    const price = vehicle.price;

    return (
        <div className="listing-card">
            <h3 className="listing-title">{title}</h3>

            <div className="listing-meta">
                {[make, model, year].filter(Boolean).join(" · ")}
            </div>

            <div className="listing-price">
                {moneyEUR(price)}
            </div>

            {vehicle.id && (
                <Link to={`/listings/${vehicle.id}`}>Details ansehen</Link>
            )}
        </div>
    );
}
