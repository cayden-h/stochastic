import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
