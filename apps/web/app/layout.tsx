import type { Metadata } from "next";
import { DM_Sans, Space_Mono } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
});

const spaceMono = Space_Mono({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-space-mono",
});

export const metadata: Metadata = {
  title: "SchemaZero — Schema Change Detection",
  description:
    "SchemaZero watches your database schema. The moment something changes, it analyzes impact, scores risk, and notifies your team — before anything breaks.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${dmSans.variable} ${spaceMono.variable}`}>
      <body className="bg-[#0a0a0a] text-white font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
