import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The same-origin proxy lets LAN reviewers use one accessible port. Production
// deployments can override the client base with VITE_API_BASE.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",
    headers: { "Cache-Control": "no-store" },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
