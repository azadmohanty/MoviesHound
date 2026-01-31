"use client";

import React, { useState, useEffect } from "react";

// Initial fallback sites
const DEFAULT_SITES: Record<string, string> = {
    "https://moviesmod.town/": "MoviesMod",
    "https://moviesleech.zip/": "MoviesLeech",
    "https://rogmovies.world/": "RogMovies",
    "https://new3.hdhub4u.fo/": "HDHub4u",
    "https://vegamovies.kg/": "VegaMovies",
    "https://bolly4u.fyi/": "Bolly4u"
};

type SearchResult = {
    title: string;
    link: string;
    site: string;
};

type SiteStatus = {
    name: string;
    status: "idle" | "loading" | "success" | "error" | "blocked";
    count: number;
    message?: string;
};

type Category = "all" | "international" | "indian" | "anime";

// BRAND MAPPING: Define which brand belongs to which category
const CATEGORY_MAP: Record<string, Category[]> = {
    "MOVIESMOD": ["international", "anime"],
    "VEGAMOVIES": ["international"],
    "BOLLY4U": ["international", "indian"],
    "HDHUB4U": ["international", "indian"],
    "MOVIESLEECH": ["indian"],
    "ROGMOVIES": ["indian"],
    "ANIMEFLIX": ["anime"],
    "GOKUHD": ["anime"],
    // Fallback: if a site isn't listed here, it appears in "all"
};

export default function Home() {
    const [query, setQuery] = useState("");
    const [category, setCategory] = useState<Category>("all");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [sites, setSites] = useState(DEFAULT_SITES);
    const [statuses, setStatuses] = useState<Record<string, SiteStatus>>({});
    const [isSyncing, setIsSyncing] = useState(false);

    // TRACKING: Prevent race conditions from old searches
    const searchId = React.useRef(0);

    // Load synced sites on mount AND refresh in background
    useEffect(() => {
        // 1. Load local immediately (fastest)
        const saved = localStorage.getItem("movie_sites");
        if (saved) {
            try {
                setSites(JSON.parse(saved));
            } catch (e: unknown) {
                console.error("Failed to parse saved sites", e);
            }
        }

        // 2. Refresh from Server (Silent Sync)
        // Since the server now caches the result for 6 hours, this is very cheap.
        // It ensures the user always has up-to-date sites without clicking anything.
        syncSites(true);
    }, []);

    const syncSites = async (isSilent = false) => {
        setIsSyncing(true);
        try {
            const res = await fetch("/api/sync");
            if (!res.ok) throw new Error("Sync failed");
            const data = await res.json();
            setSites(data.sites);
            localStorage.setItem("movie_sites", JSON.stringify(data.sites));

            if (!isSilent) {
                alert(`Synced! Found ${Object.keys(data.sites).length} active sites.`);
            }
        } catch (e: unknown) {
            if (!isSilent) alert("Failed to sync sites. Using offline defaults.");
        } finally {
            setIsSyncing(false);
        }
    };

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        // 1. Increment ID: This invalidates all previous pending requests
        const currentId = searchId.current + 1;
        searchId.current = currentId;

        setResults([]); // Clear previous
        const newStatuses: Record<string, SiteStatus> = {};

        // 2. FILTER SITES based on Category
        const activeSites = Object.entries(sites).filter(([url, name]) => {
            if (category === "all") return true;

            const siteCategories = CATEGORY_MAP[name.toUpperCase()] || [];
            return siteCategories.includes(category);
        });

        // Initialize statuses
        activeSites.forEach(([url, name]) => {
            newStatuses[url] = { name, status: "loading", count: 0 };
        });
        setStatuses(newStatuses);

        // FAN-OUT: Trigger all fetches in parallel
        activeSites.forEach(([url, name]) => {
            // Explicitly cast to prevent 'unknown' errors
            const siteUrl = url as string;
            const siteName = name as string;

            fetch(`/api/search?q=${encodeURIComponent(query)}&url=${encodeURIComponent(siteUrl)}&name=${encodeURIComponent(siteName)}`)
                .then((res) => res.json())
                .then((data: { results?: SearchResult[], status?: string }) => {
                    // CHECK: Is this still the active search?
                    if (searchId.current !== currentId) return;

                    const resultCount = data.results ? data.results.length : 0;
                    const apiStatus = data.status || "unknown"; // "ok", "blocked", "error"

                    // Determine Final Status
                    let finalStatus: SiteStatus["status"] = "error";
                    let msg = "";

                    if (resultCount > 0) {
                        finalStatus = "success";
                    } else {
                        // Differentiate why it failed
                        if (apiStatus === "ok") {
                            finalStatus = "idle"; // "idle" (Yellow) = Checked but found nothing
                            msg = "(0)";
                        } else if (apiStatus === "blocked") {
                            finalStatus = "blocked"; // New status for blocked (Purple?)
                            msg = "(Blocked)";
                        } else {
                            finalStatus = "error"; // "error" (Red) = Network/Parse error
                            msg = "(Error)";
                        }
                    }

                    setResults((prev) => [...prev, ...(data.results || [])]);
                    setStatuses((prev) => ({
                        ...prev,
                        [siteUrl]: {
                            ...prev[siteUrl],
                            status: finalStatus,
                            count: resultCount,
                            message: msg
                        },
                    }));
                })
                .catch(() => {
                    if (searchId.current !== currentId) return;
                    setStatuses((prev) => ({
                        ...prev,
                        [siteUrl]: { ...prev[siteUrl], status: "error", count: 0, message: "(Fail)" },
                    }));
                });
        });
    };

    return (
        <main>
            <div className="actions">
                <button className="btn" onClick={() => syncSites(false)} disabled={isSyncing}>
                    {isSyncing ? "⚡ Syncing..." : "⚡ Refresh Sites"}
                </button>
            </div>

            <h1>MoviesHound</h1>
            <p className="subtitle">Search Once. Watch Anywhere.</p>

            {/* Category Filter Pills */}
            <div className="category-filter">
                {(["all", "international", "indian", "anime"] as Category[]).map((cat) => (
                    <button
                        key={cat}
                        className={`filter-pill ${category === cat ? "active" : ""}`}
                        onClick={() => setCategory(cat)}
                        type="button"
                    >
                        {cat === "all" ? "All" : cat.charAt(0).toUpperCase() + cat.slice(1)}
                    </button>
                ))}
            </div>

            <form onSubmit={handleSearch}>
                <input
                    type="text"
                    className="search-box"
                    placeholder={`Search ${category === 'all' ? 'Movies' : category + ' movies'}...`}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    autoFocus
                />
            </form>

            {/* Progress Indicators - Only show for filtered sites */}
            {Object.keys(statuses).length > 0 && (
                <div className="status-bar">
                    {Object.entries(statuses).map(([url, s]) => (
                        <div key={url} className={`status-indicator ${s.status}`}>
                            <div className="dot"></div>
                            <span>{s.name}</span>
                            {/* Show message (Blocked/Error/0) OR count if success */}
                            {s.status === "success" && s.count > 0 && <span>({s.count})</span>}
                            {s.status !== "success" && s.message && <span style={{ opacity: 0.8, fontSize: '0.75rem' }}>{s.message}</span>}
                        </div>
                    ))}
                </div>
            )}

            <div className="results-grid">
                {results.map((r, i) => (
                    <div key={i} className="result-card-container">
                        <a href={r.link} target="_blank" rel="noopener noreferrer" className="result-card">
                            <div>
                                <h3>{r.title}</h3>
                                <span className="site-badge">{r.site}</span>
                            </div>
                            <span className="arrow">↗</span>
                        </a>

                        {/* Proxy/Unlock Button */}
                        <a
                            href={`https://www.filterbypass.me/go.php?u=${encodeURIComponent(r.link)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="proxy-btn"
                            title="Bypass ISP Block (Unlock)"
                        >
                            🔓
                        </a>
                    </div>
                ))}
            </div>

            {/* Help / Info Section */}
            <div className="info-card">
                <h3>How it works</h3>
                <div className="info-grid">
                    <div className="info-item">
                        <h4>🔍 Search</h4>
                        <p>Enter a movie or series Name. We scan multiple sites in parallel for you.</p>
                    </div>
                    <div className="info-item">
                        <h4>⚡ Instant Links</h4>
                        <p>Click any result to go directly to the download page. No middlemen.</p>
                    </div>
                    <div className="info-item">
                        <h4>🛠️ Auto-Sync</h4>
                        <p>Links broken? Click <b>Refresh Sites</b> to automatically find new working URLs.</p>
                    </div>
                </div>
            </div>
        </main>
    );
}
