import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dashboard calls the FastAPI backend directly; the API base is configurable
// via VITE_API_BASE (defaults to the local backend). CORS is enabled server-side
// for the dev origin.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
