import { useEffect, useState } from "react";
import { getVehicles} from "../api/vehicles.js";
import ListingCard from "../components/ListingCard";

export default function Listings() {
    const [vehicles, setVehicles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        getVehicles()
            .then(setVehicles)
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <p className="text-gray-400">Loading…</p>;
    if (error) return <p className="text-red-500">{error}</p>;

    return (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {vehicles.map(v => (
                <ListingCard key={v.id} vehicle={v} />
            ))}
        </div>
    );
}
