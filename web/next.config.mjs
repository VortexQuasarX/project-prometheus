/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const target = process.env.SERVER_API_URL ?? "https://w6qubbix87.execute-api.ap-south-1.amazonaws.com";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${target}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
