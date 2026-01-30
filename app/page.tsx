"use client";

import { useState, useEffect } from "react";

// Initial fallback sites
const DEFAULT_SITES: Record<string, string> = {
    "https://moviesmod.town/": "MoviesMod",
    "https://moviesleech.zip/": "MoviesLeech",
    "https://rogmovies.world/": "RogMovies",
    "https://new3.hdhub4u.fo/": "HDHub4u",
    "https://vegamovies.gratis/": "VegaMovies",
};

type SearchResult = {
    title: string;
    link: string;
    site: string;
};

type SiteStatus = {
    name: string;
    status: "idle" | "loading" | "success" | "error";
    count: number;
};

export default function Home() {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [sites, setSites] = useState(DEFAULT_SITES);
    const [statuses, setStatuses] = useState<Record<string, SiteStatus>>({});
    const [isSyncing, setIsSyncing] = useState(false);

    // Load synced sites on mount
    useEffect(() => {
        const saved = localStorage.getItem("movie_sites");
        if (saved) {
            try {
                setSites(JSON.parse(saved));
            } catch (e) {
                console.error("Failed to parse saved sites", e);
            }
        }
    }, []);

    const syncSites = async () => {
        setIsSyncing(true);
        try {
            const res = await fetch("/api/sync");
            if (!res.ok) throw new Error("Sync failed");
            const data = await res.json();
            setSites(data.sites);
            localStorage.setItem("movie_sites", JSON.stringify(data.sites));
            alert(`Synced! Found ${Object.keys(data.sites).length} active sites.`);
        } catch (e) {
            alert("Failed to sync sites. Using offline defaults.");
        } finally {
            setIsSyncing(false);
        }
    };

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setResults([]); // Clear previous
        const newStatuses: Record<string, SiteStatus> = {};

        // Initialize statuses
        Object.entries(sites).forEach(([url, name]) => {
            newStatuses[url] = { name, status: "loading", count: 0 };
        });
        setStatuses(newStatuses);

        // FAN-OUT: Trigger all fetches in parallel
        Object.entries(sites).forEach(([url, name]) => {
            fetch(`/api/search?q=${encodeURIComponent(query)}&url=${encodeURIComponent(url)}&name=${encodeURIComponent(name)}`)
                .then((res) => res.json())
                .then((data) => {
                    if (data.results) {
                        setResults((prev) => [...prev, ...data.results]);
                        setStatuses((prev) => ({
                            ...prev,
                            [url]: { ...prev[url], status: "success", count: data.results.length },
                        }));
                    } else {
                        setStatuses((prev) => ({
                            ...prev,
                            [url]: { ...prev[url], status: "error", count: 0 },
                        }));
                    }
                })
                .catch(() => {
                    setStatuses((prev) => ({
                        ...prev,
                        [url]: { ...prev[url], status: "error", count: 0 },
                    }));
                });
        });
    };

    return (
        <main>
            <div className="actions">
                <button className="btn" onClick={syncSites} disabled={isSyncing}>
                    {isSyncing ? "⚡ Syncing..." : "⚡ Refresh Sites"}
                </button>
            </div>

            <h1>MoviesHound</h1>

            <form onSubmit={handleSearch}>
                <input
                    type="text"
                    className="search-box"
                    placeholder="Enter Movie Name (e.g. Batman)..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    autoFocus
                />
            </form>

            {/* Progress Indicators */}
            {Object.keys(statuses).length > 0 && (
                <div className="status-bar">
                    {Object.entries(statuses).map(([url, s]) => (
                        <div key={url} className={`status-indicator ${s.status}`}>
                            <div className="dot"></div>
                            <span>{s.name}</span>
                            {s.count > 0 && <span>({s.count})</span>}
                        </div>
                    ))}
                </div>
            )}

            <div className="results-grid">
                {results.map((r, i) => (
                    <a key={i} href={r.link} target="_blank" rel="noopener noreferrer" className="result-card">
                        <div>
                            <h3>{r.title}</h3>
                            <span className="site-badge">{r.site}</span>
                        </div>
                        <span>↗</span>
                    </a>
                ))}
            </div>
        </main>
    );
}
