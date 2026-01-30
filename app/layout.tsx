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
            <body>{children}</body>
        </html>
    );
}
