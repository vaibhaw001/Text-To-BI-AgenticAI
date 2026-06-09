import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Agentic Text-to-BI Dashboard",
  description: "Relational modeling and grammar of graphics natural language interface.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-zinc-950 text-zinc-50 font-sans">
        {children}
      </body>
    </html>
  );
}
