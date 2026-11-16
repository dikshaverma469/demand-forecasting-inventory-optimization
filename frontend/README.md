# Demand Forecasting & Inventory Optimization: Frontend

React (Vite) dashboard with sign in / create account, built on the
[backend API](../backend). Charts use Recharts and requests use Axios.

Built by Diksha Verma.

## Run locally

```bash
npm install
cp .env.example .env     # points at http://127.0.0.1:8000
npm run dev
```

Open http://localhost:5173. Start the backend first (see `../backend/README.md`).

## Deploy

Set `VITE_API_URL` to your deployed backend URL, then `npm run build`
and publish the `dist/` folder. On the backend, set `FRONTEND_ORIGINS` to the
frontend's URL and `JWT_SECRET` to a long random string.
