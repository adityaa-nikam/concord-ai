const backendUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://concord-ai-production.up.railway.app').replace(/\/$/, '');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: '/health',
        destination: `${backendUrl}/api/health`,
      },
    ];
  },
};

module.exports = nextConfig;
