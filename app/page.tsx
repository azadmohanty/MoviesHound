"use client";
import React, { useState, useEffect } from "react";

// NEW DEFAULTS (Fresh Start)
type SiteConfig = {
    name: string;
    categories: string[];
};

const DEFAULT_SITES: Record<string, SiteConfig> = {
    "https://moviesmod.town/": { name: "MoviesMod", categories: ["international", "korean", "anime"] },
    "https://vegamovies.gratis/": { name: "VegaMovies", categories: ["international"] },
    "https://bolly4u.cl/": { name: "Bolly4u", categories: ["international", "indian"] },
    "https://moviesleech.zip/": { name: "MoviesLeech", categories: ["indian"] },
    "https://rogmovies.world/": { name: "RogMovies", categories: ["indian"] },
    "https://animeflix.dad/": { name: "Animeflix", categories: ["anime"] },
    "https://onlykdrama.top/": { name: "OnlyKDrama", categories: ["korean"] },
    "https://mkvdrama.net/": { name: "MKVDrama", categories: ["korean"] },
    "https://bollyflix.sarl/": { name: "BollyFlix", categories: ["international", "indian"] }
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

type Category = "all" | "international" | "indian" | "anime" | "korean";

export default function Home() {
    const [query, setQuery] = useState("");
    const [category, setCategory] = useState<Category>("all");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [sites, setSites] = useState<Record<string, SiteConfig>>(DEFAULT_SITES);
    const [statuses, setStatuses] = useState<Record<string, SiteStatus>>({});
    const [isSyncing, setIsSyncing] = useState(false);
    const [syncMessage, setSyncMessage] = useState<string>("");

    const searchId = React.useRef(0);

    useEffect(() => {
        const saved = localStorage.getItem("movie_sites_v2");
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                // Simple validation to ensure it's the new format
                const sample = Object.values(parsed)[0] as any;
                if (sample && typeof sample === 'object' && 'categories' in sample) {
                    setSites(parsed);
                }
            } catch (e) { }
        }
        syncSites(true);
    }, []);

    const syncSites = async (isSilent = false) => {
        setIsSyncing(true);
        setSyncMessage("Syncing...");
        try {
            const res = await fetch("/api/sync");
            if (!res.ok) throw new Error("Sync failed");
            const data = await res.json();

            // CLIENT-SIDE SAFETY DEDUPLICATION
            const rawSites = data.sites; // Now Record<string, SiteConfig>
            const uniqueSites: Record<string, SiteConfig> = {};
            const grouped: Record<string, string[]> = {};

            Object.entries(rawSites).forEach(([url, config]) => {
                const c = config as SiteConfig;
                const n = c.name.toUpperCase();
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

            // MERGE LOGIC: Merge based on BRAND NAME (Value) instead of URL (Key)
            // 1. Convert Defaults to Map<Name, URL>
            const defaultsByName: Record<string, string> = {};
            Object.entries(DEFAULT_SITES).forEach(([url, config]) => {
                defaultsByName[config.name] = url;
            });

            // 2. Convert Sync Results to Map<Name, URL>
            const syncByName: Record<string, string> = {};
            Object.entries(uniqueSites).forEach(([url, config]) => {
                syncByName[config.name] = url;
            });

            // 3. Merge Sync into Defaults (Sync overwrites Defaults if Name matches)
            const mergedByName = { ...defaultsByName, ...syncByName };

            // 4. Convert back to Map<URL, Config> for the App state
            const finalSites: Record<string, SiteConfig> = {};
            Object.entries(mergedByName).forEach(([name, url]) => {
                // We need to recover the config object. 
                // Priority: Sync Result > Default
                let config = uniqueSites[url];
                if (!config) config = DEFAULT_SITES[url];

                // If we still can't find it (rare edge case of mixed sources), try to find by name in defaults
                if (!config) {
                    const defMatch = Object.values(DEFAULT_SITES).find(c => c.name === name);
                    if (defMatch) config = defMatch;
                }

                if (config) finalSites[url] = config;
            });

            setSites(finalSites);
            localStorage.setItem("movie_sites_v2", JSON.stringify(finalSites));

            if (!isSilent) {
                setSyncMessage(`Synced! Active Config: ${Object.keys(finalSites).length} sites.`);
                setTimeout(() => setSyncMessage(""), 3000);
            } else {
                setSyncMessage("");
            }
        } catch (e: unknown) {
            console.error(e);
            if (!isSilent) {
                setSyncMessage("Failed to sync sites. Using offline defaults.");
                setTimeout(() => setSyncMessage(""), 3000);
            }
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

        const activeSites = Object.entries(sites).filter(([url, config]) => {
            if (category === "all") return true;
            return config.categories.includes(category);
        });

        activeSites.forEach(([url, config]) => {
            newStatuses[url] = { name: config.name, status: "loading", count: 0 };
        });
        setStatuses(newStatuses);

        activeSites.forEach(([url, config]) => {
            const siteUrl = url as string;
            const siteName = config.name;

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

                    // Simple Deduplication: Filter out results that have same Title AND same Site
                    setResults((prev) => {
                        const incoming = data.results || [];
                        const combined = [...prev, ...incoming];
                        // Removing duplicates based on Link is better than Title alone
                        const unique = new Map();
                        combined.forEach(item => {
                            if (!unique.has(item.link)) unique.set(item.link, item);
                        });
                        return Array.from(unique.values());
                    });

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
            <div className="header">
                <div className="brand-icon">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM10 16.5V7.5L16 12L10 16.5Z" fill="url(#brand-grad)" />
                        <defs>
                            <linearGradient id="brand-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                                <stop stopColor="#60a5fa" />
                                <stop offset="1" stopColor="#2563eb" />
                            </linearGradient>
                        </defs>
                    </svg>
                </div>
                <h1>MoviesHound</h1>
                <p className="subtitle">Search Once. Watch Anywhere.</p>
            </div>

            <div className="search-section">
                <form onSubmit={handleSearch}>
                    <div className="search-wrapper">
                        <input
                            type="text"
                            className="search-box"
                            placeholder={`Search ${category === 'all' ? 'Movies & Series' : category + ' Content'}...`}
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            autoFocus
                        />
                        <button type="submit" className="search-btn">🔍</button>
                    </div>
                </form>

                <div className="category-filter">
                    {(["all", "international", "indian", "anime", "korean"] as Category[]).map((cat) => (
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
            </div>

            {Object.keys(statuses).length > 0 && (
                <div className="status-container">
                    <div className="status-bar">
                        {Object.entries(statuses).map(([url, s]) => (
                            <div key={url} className={`status-indicator ${s.status}`}>
                                <div className="dot"></div>
                                <span>{s.name}</span>
                                {s.status === "success" && s.count > 0 && <span>({s.count})</span>}
                                {s.status !== "success" && s.message && <span className="status-msg">{s.message}</span>}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <div className="results-grid">
                {results.map((r, i) => (
                    <div key={i} className="result-card-container">
                        <a href={r.link} target="_blank" rel="noopener noreferrer" className="result-card">
                            <div className="card-content">
                                <h3>{r.title}</h3>
                                <div className="card-meta">
                                    <span className="site-badge">{r.site}</span>
                                </div>
                            </div>
                            <span className="arrow">↗</span>
                        </a>
                        <a
                            href={`https://proxyium.com/search?url=${encodeURIComponent(r.link)}`}
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

            <div className="bottom-actions">
                <button className="sync-btn" onClick={() => syncSites(false)} disabled={isSyncing}>
                    {isSyncing ? "⚡ Syncing Database..." : "⚡ Refresh Working Sites"}
                </button>
                {syncMessage && <span className="sync-msg-toast">{syncMessage}</span>}
            </div>

            <div className="info-section">
                <div className="info-header">
                    <h3>The MoviesHound Advantage</h3>
                    <p>Designed for speed, built for reliability.</p>
                </div>
                <div className="info-steps">
                    <div className="step">
                        <div className="step-icon">01</div>
                        <h4>Instant Search</h4>
                        <p>We query 10+ providers in parallel to find the best quality links in seconds.</p>
                    </div>
                    <div className="step">
                        <div className="step-icon">02</div>
                        <h4>No ISP Blocks</h4>
                        <p>Use the unlock icon to bypass region restrictions and provider blocks instantly.</p>
                    </div>
                    <div className="step">
                        <div className="step-icon">03</div>
                        <h4>Daily Sync</h4>
                        <p>Our autonomous bot verifies URLs daily to ensure you never hit a dead link.</p>
                    </div>
                </div>
            </div>
        </main>
    );
}
