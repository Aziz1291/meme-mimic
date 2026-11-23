// Settings for the Vite dev server (the program behind "npm run dev").
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    // Any request starting with /api is forwarded to the backend container on port 8000.
    // The browser only ever talks to localhost:5173, so there are no CORS errors.
    proxy: { '/api': 'http://127.0.0.1:8000' },
    // The project is on the Windows drive: check files regularly instead of waiting
    // for change events, which don't always arrive there.
    watch: { usePolling: true },
  },
})
