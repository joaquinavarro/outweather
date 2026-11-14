/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  // Static export: the built site is plain files in `out/`, which the FastAPI
  // process serves from `/`. That gives one command and one port, no Node at runtime.
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
