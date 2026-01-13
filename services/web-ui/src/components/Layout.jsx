import { Outlet, Link, NavLink } from "react-router-dom";

export default function Layout() {
    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-100">
            <header className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur">
                <div className="mx-auto flex w-full max-w-screen-2xl items-center justify-between px-4 py-3">
                    <Link to="/listings" className="text-sm font-semibold tracking-tight">
                        VLP
                    </Link>

                    <nav className="flex gap-4 text-sm">
                        <NavLink
                            to="/listings"
                            className={({ isActive }) =>
                                isActive
                                    ? "text-zinc-100 underline underline-offset-8"
                                    : "text-zinc-400 hover:text-zinc-100"
                            }
                        >
                            Inserate
                        </NavLink>
                    </nav>
                </div>
            </header>

            <main className="w-full">
                <Outlet />
            </main>
        </div>
    );
}
