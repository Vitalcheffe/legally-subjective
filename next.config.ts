import type { NextConfig } from "next";

// Static export — the whole site is plain HTML, served anywhere.
// No server, no API routes, no database, no runtime dependencies.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
