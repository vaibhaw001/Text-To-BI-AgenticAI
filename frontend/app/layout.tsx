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
      className="h-full antialiased dark"
      suppressHydrationWarning
    >
      <body 
        className="min-h-full flex flex-col bg-zinc-950 text-zinc-50 font-sans"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
