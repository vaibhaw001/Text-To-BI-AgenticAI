import type { Metadata } from "next";
import "./globals.css";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

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
      className="h-full antialiased"
      suppressHydrationWarning
    >
      <body 
        className="min-h-full flex flex-col bg-gradient-to-tr from-[#f0f4ff] via-[#f5f3ff] to-[#fffaf0] text-zinc-800 font-sans"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
