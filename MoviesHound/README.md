# MoviesHound

High-performance, parallel movie search engine.
Built with Next.js (Frontend) and Python (Scraping API).

## 🚀 Quick Start (Recommended)

The best way to run this locally (so the Python API works) is using the Vercel CLI.

1.  **Install Vercel CLI**:
    ```bash
    npm install -g vercel
    ```

2.  **Run the App**:
    ```bash
    cd web
    vercel dev
    ```
    This mimics the production environment and runs both the React frontend and Python backend together.

## 🛠️ Deployment

1.  **Push to GitHub**
2.  **Import to Vercel**:
    - Go to [vercel.com/new](https://vercel.com/new)
    - Select your repository
    - Set the **Root Directory** to `web` (IMPORTANT!)
    - Click **Deploy**

Vercel will automatically detect the Next.js app and the Python API files.

## 📂 Structure

-   `app/`: React Frontend (Fan-Out Search Logic)
-   `api/`: Python Backend (Cloudscraper Logic)
