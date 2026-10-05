import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import Topbar from "@/components/layout/Topbar";

export const metadata: Metadata = {
  metadataBase: new URL("https://google-photos-ai-discovery-engine.vercel.app"),
  title: {
    template: "%s | Discovery Engine",
    default: "Discovery Engine — Photo Retrieval Insights",
  },
  description: "AI-Powered Photo Retrieval Discovery Engine for Google Photos product insights",
  openGraph: {
    title: "Discovery Engine — Photo Retrieval Insights",
    description: "AI-Powered Photo Retrieval Discovery Engine for Google Photos product insights",
    url: "https://google-photos-ai-discovery-engine.vercel.app",
    siteName: "Discovery Engine",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
      }
    ],
    locale: "en_US",
    type: "website",
  },
  icons: {
    icon: "/favicon.jpg",
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Topbar />
        <div className="app-layout">
          <Sidebar />
          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
