import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The e2e suite builds its own copy (e2e/README.md), so it never overwrites the build the Mac app serves.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  devIndicators: false, // the Next.js "N" button showed on the projector in every dev-server demo
  turbopack: {
    root: path.resolve(import.meta.dirname),
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
