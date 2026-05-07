import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import { defineConfig as defineLovableConfig } from "@lovable.dev/vite-tanstack-config";

export default process.env.VITE_STATIC_BUILD 
  ? defineConfig({
      plugins: [react(), tsconfigPaths()],
      build: {
        outDir: "dist",
      }
    })
  : defineLovableConfig();
