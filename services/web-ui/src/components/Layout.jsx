import { Outlet, Link, NavLink } from "react-router-dom";

export default function Layout() {
    return (
        <div className="min-h-screen bg-zinc-50 text-zinc-900">
            <header className="sticky top-0 z-10 border-b bg-white/90 backdrop-blur">
                <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
                    <Link to="/listings" className="text-lg font-semibold">
                        VLP
                    </Link>
                    <nav className="flex gap-4 text-sm">
                        <NavLink to="/listings" className={({isActive}) => isActive ? "font-semibold" : "text-zinc-600 hover:text-zinc-900"}>
                            Inserate
                        </NavLink>
                    </nav>
                </div>
            </header>

            <main className="mx-auto max-w-6xl px-4 py-6">
                <Outlet />
            </main>

            <footer className="border-t bg-white">
                <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-zinc-500">
                    VLP Demo UI — Frontend ist nicht Bestandteil der Messungen.
                </div>
            </footer>
        </div>
    );
}
