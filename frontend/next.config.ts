import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    // Fallback Railway backend URL — override in Vercel dashboard to change
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "https://web-production-1f3c6.up.railway.app",
  },
};

export default nextConfig;
