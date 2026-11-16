# AI-Driven Demand Forecasting & Inventory Optimization

An end-to-end machine learning system that forecasts product demand and generates
inventory optimization recommendations (safety stock, reorder points, EOQ) for a
multi-category e-commerce supply chain.

Built on the **DataCo Smart Supply Chain dataset** (~180,000 order records across
50 product categories, 2015–2018).

## What this project does

1. Aggregates raw order-level transaction data into daily demand time series per category
2. Trains an **XGBoost** regression model and a **Prophet** time-series model to forecast demand
3. Combines both models into a weighted **ensemble** for improved accuracy
4. Uses **SHAP** to explain which features drive each prediction
5. Calculates **safety stock**, **reorder point**, and **Economic Order Quantity (EOQ)**
   for each product category using classical inventory theory (Silver, Pyke & Thomas, 2017)
6. Serves everything through a **FastAPI** backend, consumed by a React dashboard

## Results

| Model | WAPE (Weighted Absolute Percentage Error) |
|---|---|
| XGBoost alone | 60.33% (on Camping & Hiking category) |
| Prophet alone | 21.18% |
| **Ensemble (XGBoost 20% / Prophet 80%)** | **11.56%** |
| XGBoost across all top 15 categories | 27.75% |

The ensemble approach consistently outperformed either individual model — consistent
with published forecasting literature (e.g. the M5 Forecasting Competition) showing
that ensemble methods reduce error beyond what any single model achieves alone.

**SHAP feature importance** identified the 30-day rolling average of demand as the
single strongest predictor, followed by the 7-day rolling average and recent lag
values — indicating that near-term historical demand trend is more informative than
calendar effects (day-of-week, month) for this dataset.

## Tech stack

- **Data processing**: pandas, numpy
- **Machine learning**: XGBoost, Prophet (Facebook/Meta), scikit-learn
- **Explainability**: SHAP
- **API**: FastAPI, uvicorn
- **Frontend**: React (Vite), Recharts, Axios — see [demand-forecast-frontend](https://github.com/dikshaverma469/demand-forecast-frontend)

## Project structure

## Dataset

This project uses the **DataCo Smart Supply Chain** dataset, which is not included in
this repository due to file size. To reproduce:

1. Download the dataset (search "DataCo Smart Supply Chain Dataset" on Kaggle)
2. Place `DataCoSupplyChainDataset.csv` in the `data/` folder
3. Run `notebooks/01_eda.ipynb` to generate `data/daily_demand_by_category.csv`

## Running locally

```bash
pip install -r requirements.txt

# Training scripts (run from inside src/)
cd src
python train_xgboost.py
python train_prophet.py
python ensemble.py
python shap_explain.py
cd ..

# Start the API from the project root
uvicorn src.api:app --reload
```

API will be available at `http://127.0.0.1:8000`, with interactive docs at
`http://127.0.0.1:8000/docs`.

## API endpoints

| Endpoint | Description |
|---|---|
| `POST /auth/register` | Create an account (username, password, optional full name) and sign in |
| `POST /auth/login` | Sign in and receive an access token |
| `GET /auth/me` | The signed-in user |
| `GET /categories` | List all available product categories |
| `GET /forecast/{category_name}` | Predicted next-day demand for a category |
| `GET /inventory/{category_name}` | Safety stock, reorder point, EOQ for a category |
| `GET /history/{category_name}` | Recent daily demand, used by the dashboard chart |
| `GET /dashboard-summary` | Full inventory plan across top 15 categories |

All endpoints except `/` and the `/auth/*` sign-in routes require an
`Authorization: Bearer <token>` header.

## Accounts and login

Users are stored in a local SQLite file (`data/users.db`) with scrypt-hashed
passwords. Sessions use signed tokens that expire after 24 hours.

| Environment variable | Purpose |
|---|---|
| `JWT_SECRET` | Secret used to sign tokens. **Set this in production.** If unset, a random one is created in `data/.jwt_secret` for local development. |
| `FRONTEND_ORIGINS` | Comma-separated URLs of your deployed frontend, allowed by CORS. |
| `AUTH_DB_PATH` | Optional path for the users database file. |
| `TOKEN_HOURS` | Optional token lifetime in hours (default 24). |

## Methodology notes

- **Chronological train/test split** was used throughout (80/20) — never randomly
  shuffled — to avoid lookahead bias inherent to time series data.
- **Lag and rolling-average features** are shifted before calculation to prevent
  data leakage (a feature must never see the value it's trying to predict).
- Categories with very low daily order volume were filtered out of training, as
  percentage-based error metrics (MAPE) become unstable and misleading on near-zero
  actuals; WAPE is reported alongside MAPE as a more robust metric for this reason.
- Inventory optimization assumes a 7-day lead time and standard cost parameters, as
  the dataset does not include actual supplier lead times or holding/ordering costs.
  These are configurable via the API's query parameters.

## Author

Diksha Verma — final-year B.Tech ECE student, IGDTUW