import type { Metadata } from "next";
import React from "react";
import "./globals.css";

export const metadata: Metadata = {
    title: "MoviesHound",
    description: "High-performance parallel movie search engine.",
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
