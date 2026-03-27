/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow large video uploads (50MB)
  experimental: {
    serverActions: {
      bodySizeLimit: "50mb",
    },
  },
  // Exclude ffmpeg-static from server-side bundle issues on Vercel
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.externals = [...(config.externals || []), "ffmpeg-static"];
    }
    return config;
  },
};

export default nextConfig;
