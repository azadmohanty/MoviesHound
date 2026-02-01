"use client";

import React, { useState, useEffect } from "react";

// NEW DEFAULTS (Fresh Start)
const DEFAULT_SITES: Record<string, string> = {
    "https://moviesmod.town/": "MoviesMod",
    "https://vegamovies.gratis/": "VegaMovies",
    "https://bolly4u.cl/": "Bolly4u",
    "https://moviesleech.zip/": "MoviesLeech",
    "https://rogmovies.world/": "RogMovies",
    "https://animeflix.dad/": "Animeflix"
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

// BRAND MAPPING (Fresh Rules)
const CATEGORY_MAP: Record<string, Category[]> = {
    "MOVIESMOD": ["international"],
    "VEGAMOVIES": ["international"],
    "BOLLY4U": ["international", "indian"],
    "MOVIESLEECH": ["indian"],
    "ROGMOVIES": ["indian"],
    "ANIMEFLIX": ["anime"],
};

export default function Home() {
    const [query, setQuery] = useState("");
    const [category, setCategory] = useState<Category>("all");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [sites, setSites] = useState(DEFAULT_SITES);
    const [statuses, setStatuses] = useState<Record<string, SiteStatus>>({});
    const [isSyncing, setIsSyncing] = useState(false);

    const searchId = React.useRef(0);

    useEffect(() => {
        const saved = localStorage.getItem("movie_sites");
        if (saved) {
            try { setSites(JSON.parse(saved)); } catch (e) { }
        }
        syncSites(true);
    }, []);

    const syncSites = async (isSilent = false) => {
        setIsSyncing(true);
        try {
            const res = await fetch("/api/sync");
            if (!res.ok) throw new Error("Sync failed");
            const data = await res.json();

            // CLIENT-SIDE SAFETY DEDUPLICATION
            const rawSites = data.sites;
            const uniqueSites: Record<string, string> = {};
            const grouped: Record<string, string[]> = {};

            Object.entries(rawSites).forEach(([url, name]) => {
                const n = (name as string).toUpperCase();
                if (!grouped[n]) grouped[n] = [];
                grouped[n].push(url);
            });

            Object.entries(grouped).forEach(([upperName, urls]) => {
                let bestUrl = urls[0];
                urls.forEach(u => {
                    if (u.startsWith('https') && !bestUrl.startsWith('https')) bestUrl = u;
                    else if (u.length < bestUrl.length && u.startsWith('https') === bestUrl.startsWith('https')) bestUrl = u;
                });
                uniqueSites[bestUrl] = rawSites[bestUrl];
            });

            // MERGE: Defaults + API Results (API wins collisions)
            // This ensures if API only finds 1 site, we still keep the others from defaults
            const mergedSites = { ...DEFAULT_SITES, ...uniqueSites };

            setSites(mergedSites);
            localStorage.setItem("movie_sites", JSON.stringify(mergedSites));

            if (!isSilent) {
                alert(`Synced! Active Config: ${Object.keys(mergedSites).length} sites.`);
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

        const currentId = searchId.current + 1;
        searchId.current = currentId;

        setResults([]);
        const newStatuses: Record<string, SiteStatus> = {};

        const activeSites = Object.entries(sites).filter(([url, name]) => {
            if (category === "all") return true;
            const siteCategories = CATEGORY_MAP[name.toUpperCase()] || ["all"];
            return siteCategories.includes(category);
        });

        activeSites.forEach(([url, name]) => {
            newStatuses[url] = { name, status: "loading", count: 0 };
        });
        setStatuses(newStatuses);

        activeSites.forEach(([url, name]) => {
            const siteUrl = url as string;
            const siteName = name as string;

            fetch(`/api/search?q=${encodeURIComponent(query)}&url=${encodeURIComponent(siteUrl)}&name=${encodeURIComponent(siteName)}`)
                .then((res) => res.json())
                .then((data: { results?: SearchResult[], status?: string }) => {
                    if (searchId.current !== currentId) return;

                    const resultCount = data.results ? data.results.length : 0;
                    const apiStatus = data.status || "unknown";

                    let finalStatus: SiteStatus["status"] = "error";
                    let msg = "";

                    if (resultCount > 0) {
                        finalStatus = "success";
                    } else {
                        if (apiStatus.startsWith("ok")) {
                            finalStatus = "idle";
                            msg = "(0)";
                        } else if (apiStatus === "blocked") {
                            finalStatus = "blocked";
                            msg = "(Blocked)";
                        } else {
                            finalStatus = "error";
                            msg = `(${apiStatus})`;
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

            {Object.keys(statuses).length > 0 && (
                <div className="status-bar">
                    {Object.entries(statuses).map(([url, s]) => (
                        <div key={url} className={`status-indicator ${s.status}`}>
                            <div className="dot"></div>
                            <span>{s.name}</span>
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
