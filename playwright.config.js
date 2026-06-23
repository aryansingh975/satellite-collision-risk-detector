import { defineConfig, devices } from "@playwright/test";

const pythonBin =
  process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60000,
  retries: 0,
  reporter: [["list"]],

  use: {
    baseURL: "http://localhost:5173",
    headless: true,
    launchOptions: {
      args: ["--use-gl=swiftshader"],
    },
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: [
    {
      // Internal imports use `app.*` so PYTHONPATH must include backend/.
      command: `${pythonBin} -m uvicorn app.main:app --host 0.0.0.0 --port 8000`,
      port: 8000,
      reuseExistingServer: true,
      timeout: 30000,
      env: { PYTHONPATH: "backend" },
    },
    {
      command: "npm --prefix frontend run dev",
      port: 5173,
      reuseExistingServer: true,
      timeout: 30000,
    },
  ],
});
