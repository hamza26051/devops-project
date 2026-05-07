import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  // Force static output for Vercel compatibility
  start: {
    ssr: false,
    output: "static",
    // Pre-render your key routes for SEO/performance
    prerender: {
      routes: [
        "/",
        "/login",
        "/signup",
        "/dashboard", 
        "/analyze",
        "/result",
        "/admin",
        "/manual"
      ],
    },
  },
  // Ensure client assets go to dist/client
  build: {
    outDir: "dist/client",
    emptyOutDir: true,
  },
});
