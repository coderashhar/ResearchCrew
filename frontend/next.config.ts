import type { NextConfig } from "next";

/**
 * On Vercel the top-level rewrites in vercel.json send /api to the Python
 * service. Running `next dev` alone has no such router, so API_PROXY points
 * at a locally running uvicorn instead.
 */
const nextConfig: NextConfig = {
  // This app is a workspace inside the repo; without a root, Next walks up
  // past it and picks up an unrelated lockfile from the home directory.
  turbopack: { root: import.meta.dirname },
  outputFileTracingRoot: import.meta.dirname,
  async rewrites() {
    const target = process.env.API_PROXY;
    return target ? [{ source: "/api/:path*", destination: `${target}/api/:path*` }] : [];
  },
};

export default nextConfig;
