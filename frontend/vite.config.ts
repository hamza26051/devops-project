import { defineConfig } from "@lovable.dev/vite-tanstack-config";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";

export default defineConfig({
  // Configure TanStack Start for static export
  start: {
    ssr: false, // Disable SSR
    output: "static", // Output static files only
    // Optional: Pre-render key routes for better SEO/performance
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
