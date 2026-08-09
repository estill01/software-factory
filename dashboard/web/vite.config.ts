import path from "node:path"

import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { configDefaults, defineConfig } from "vitest/config"

const dashboardHost = process.env.SOFTWARE_FACTORY_DASHBOARD_HOST ?? "127.0.0.1"
const dashboardPort = process.env.SOFTWARE_FACTORY_DASHBOARD_PORT ?? "8787"
const dashboardOrigin = `http://${dashboardHost}:${dashboardPort}`

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5188,
    strictPort: true,
    proxy: {
      "/api": {
        target: dashboardOrigin,
        changeOrigin: true,
        configure(proxy) {
          proxy.on("proxyReq", (proxyRequest) => {
            proxyRequest.setHeader("Origin", dashboardOrigin)
          })
        },
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4188,
    strictPort: true,
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: "react-core",
              test: /node_modules[\\/](react|react-dom|scheduler|react-router)[\\/]/,
              priority: 30,
            },
            {
              name: "data-state",
              test: /node_modules[\\/](@tanstack|jotai|zod)[\\/]/,
              priority: 20,
            },
            {
              name: "ui-core",
              test: /node_modules[\\/](@radix-ui|lucide-react|class-variance-authority|clsx|tailwind-merge)[\\/]/,
              priority: 10,
            },
          ],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
    exclude: [...configDefaults.exclude, "e2e/**"],
  },
})
