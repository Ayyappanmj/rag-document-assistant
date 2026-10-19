import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Only the Docker build sets NEXT_OUTPUT=standalone. Vercel and `npm run dev` use the normal output.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
};

export default nextConfig;
