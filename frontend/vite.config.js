import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const outDir = process.env.CHECK_BUILD === "1" ? "../.check-dist" : "../site";

export default defineConfig({
  base: "./",
  plugins: [vue()],
  build: {
    outDir,
    emptyOutDir: true
  }
});
