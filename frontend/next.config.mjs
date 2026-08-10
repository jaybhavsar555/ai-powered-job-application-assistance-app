/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8001/api/v1/:path*'
      },
      {
        source: '/static/:path*',
        destination: 'http://localhost:8001/static/:path*'
      }
    ]
  }
};

export default nextConfig;
