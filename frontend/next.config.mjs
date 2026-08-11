/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    // Docker compose publishes API as host:8001 → container:8000
    // Use 127.0.0.1 (not localhost) to avoid Windows resolving to ::1
    const apiOrigin =
      process.env.BACKEND_URL || "http://127.0.0.1:8001";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiOrigin}/api/v1/:path*`,
      },
      {
        source: "/static/:path*",
        destination: `${apiOrigin}/static/:path*`,
      },
    ];
  },
};

export default nextConfig;
