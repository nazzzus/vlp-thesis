import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import Listings from "./pages/Listings.jsx";
import VehicleDetail from "./pages/VehicleDetail";

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route element={<Layout />}>
                    <Route path="/" element={<Navigate to="/listings" replace />} />
                    <Route path="/listings" element={<Listings />} />
                    <Route path="/listings/:id" element={<VehicleDetail />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}
