import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Silences a Turbopack warning: there's a stray package-lock.json above
  // this repo (outside it) that Next would otherwise mistake for the
  // workspace root.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
