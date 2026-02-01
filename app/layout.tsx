import type { Metadata, Viewport } from "next";
import React from "react";
import "./globals.css";

export const viewport: Viewport = {
    themeColor: "#3b82f6",
    width: "device-width",
    initialScale: 1,
    maximumScale: 1,
};

export const metadata: Metadata = {
    title: "MoviesHound",
    description: "High-performance parallel movie search engine.",
    manifest: "/manifest.json",
    themeColor: "#3b82f6",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
            </head>
            <body>{children}</body>
        </html>
    );
}
