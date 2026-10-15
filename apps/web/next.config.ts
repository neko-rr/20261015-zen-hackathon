import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  async headers() {
    const noStore = [{ key: "Cache-Control", value: "private, no-store" }];
    return [
      { source: "/", headers: noStore },
      { source: "/library", headers: noStore },
      { source: "/licenses", headers: noStore },
    ];
  },
  async rewrites() {
    const destination = process.env.API_BASE_URL?.trim().replace(/\/$/, "") ?? "";
    if (!destination) {
      return [];
    }
    return [{ source: "/drawref-api/:path*", destination: `${destination}/:path*` }];
  },
  experimental: {
    // 提出後の凍結中に、ビルドが新しい版へ促さないようにする
    agentUpgrade: false,
  },
};

export default nextConfig;
