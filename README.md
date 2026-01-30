# MoviesHound

**MoviesHound** is a high-performance, privacy-focused movie search engine. It aggregates results from multiple third-party sources in parallel, providing a unified and lightning-fast search experience.

![MoviesHound](https://via.placeholder.com/800x400?text=MoviesHound+Interface)

## 🚀 Features

*   **Fan-Out Search Architecture**: Searches 5+ sites simultaneously. Results appear instantly as they are found.
*   **Anti-Bot Bypass**: Uses Python's `cloudscraper` on the backend to bypass Cloudflare protections ensuring reliable results.
*   **Smart Sync**: Automatically discovers new proxy domains (e.g., when `.town` changes to `.hub`) to keep the search engine running forever.
*   **Privacy First**: No tracking, no logs.
*   **Dark Mode**: specialized "Premium Dark" UI designed for movie enthusiasts.

## 🛠️ Tech Stack

*   **Frontend**: Next.js 14 (React), TypeScript, Vanilla CSS (Glassmorphism).
*   **Backend**: Python 3.9 (Serverless Functions), BeautifulSoup4, Cloudscraper.
*   **Deployment**: Vercel (Zero config).

## 🏃‍♂️ Quick Start (Local)

To run this locally, you need **Node.js** and **Python** installed. We recommend using the Vercel CLI to mimic the production environment.

1.  **Clone & Install**:
    ```bash
    git clone https://github.com/your-repo/movies-hound.git
    cd MoviesHound
    npm install
    pip install -r requirements.txt
    ```

2.  **Run with Vercel CLI** (Recommended):
    ```bash
    npm i -g vercel
    vercel dev
    ```
    *This runs both the Next.js frontend and Python backend on localhost:3000.*

## ⚙️ Configuration

You can manage the search sources in `api/sync.py`:

*   **Redirect Sources**: Add "Magic URLs" that auto-redirect (e.g., `vegamovies.la`).
*   **Hub Sources**: Add list sites to scrape for new domains.
*   **Ignored Domains**: Add domains to blacklist from the sync results.

## 📦 Deployment

1.  Push your code to **GitHub**.
2.  Import the repository to **Vercel**.
3.  Set the **Root Directory** to `MoviesHound`.
4.  Click **Deploy**.

## 📝 License

This project is for educational purposes only. Do not use it for illegal activities.
