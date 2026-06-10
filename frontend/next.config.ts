import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Disable automatic deep import rewriting that can target non-existent .mjs icon files
    optimizePackageImports: [],
  },
};

export default nextConfig;
