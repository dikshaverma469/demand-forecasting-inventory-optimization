import os
from pathlib import Path

import pandas as pd
import xgboost as xgb
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.auth import get_current_user, router as auth_router
from src.features import build_features, encode_category
from src.inventory_optimization import build_inventory_plan


# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "models" / "xgboost_model.json"
DATA_PATH = BASE_DIR / "data" / "daily_demand_by_category.csv"


app = FastAPI(
    title="AI Demand Forecasting & Inventory Optimization API"
)

# Allow frontend connections. In production set FRONTEND_ORIGINS to your
# deployed frontend URL(s), comma-separated.
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
] + [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sign up / sign in routes: /auth/register, /auth/login, /auth/me
app.include_router(auth_router)

# Every data endpoint below requires a signed-in user.
protected = [Depends(get_current_user)]


# Load model
model = xgb.XGBRegressor()
model.load_model(str(MODEL_PATH))

# Load demand data
daily_demand = pd.read_csv(
    DATA_PATH,
    parse_dates=["order_date"]
)


FEATURE_COLS = [
    "Category Name_code",
    "day_of_week",
    "is_weekend",
    "month",
    "week_of_year",
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
    "rolling_mean_30",
    "avg_discount_rate",
    "late_delivery_risk"
]


@app.get("/")
def root():
    return {
        "message": "Demand Forecasting & Inventory Optimization API is running"
    }


# Note: {category_name:path} lets names that contain a slash,
# like "Indoor/Outdoor Games", match the route.

@app.get("/categories", dependencies=protected)
def get_categories():
    categories = daily_demand["Category Name"].dropna().unique().tolist()
    return {"categories": categories}


@app.get("/history/{category_name:path}", dependencies=protected)
def get_history(category_name: str, days: int = Query(90, ge=7, le=365)):
    cat_df = daily_demand[
        daily_demand["Category Name"] == category_name
    ].sort_values("order_date")

    if cat_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category_name}' not found"
        )

    recent = cat_df.tail(days)

    return {
        "category": category_name,
        "points": [
            {"date": row.order_date.strftime("%Y-%m-%d"), "quantity": float(row.quantity)}
            for row in recent.itertuples()
        ],
    }


@app.get("/forecast/{category_name:path}", dependencies=protected)
def get_forecast(category_name: str, days: int = 7):

    cat_df = daily_demand[
        daily_demand["Category Name"] == category_name
    ].copy()

    if cat_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category_name}' not found"
        )

    cat_df = build_features(cat_df)
    cat_df = encode_category(
        cat_df,
        category_col="Category Name"
    )

    cat_df[["avg_discount_rate", "late_delivery_risk"]] = (
        cat_df[["avg_discount_rate", "late_delivery_risk"]].fillna(0)
    )

    cat_df = cat_df.dropna(subset=FEATURE_COLS)

    if cat_df.empty:
        raise HTTPException(
            status_code=400,
            detail="Not enough history to build features for this category"
        )

    latest_row = cat_df.iloc[[-1]][FEATURE_COLS]

    prediction = model.predict(latest_row)[0]

    return {
        "category": category_name,
        "predicted_next_day_demand": round(float(prediction), 1),
        "last_actual_demand": float(cat_df.iloc[-1]["quantity"]),
        "last_date": str(cat_df.iloc[-1]["order_date"].date())
    }


@app.get("/inventory/{category_name:path}", dependencies=protected)
def get_inventory_plan(
    category_name: str,
    lead_time_days: int = Query(7, ge=1, le=90),
    service_level: float = 0.95
):

    plan = build_inventory_plan(
        daily_demand,
        category_name,
        lead_time_days=lead_time_days,
        service_level=service_level
    )

    if "error" in plan:
        raise HTTPException(
            status_code=404,
            detail=plan["error"]
        )

    return plan


@app.get("/dashboard-summary", dependencies=protected)
def dashboard_summary():

    top_categories = (
        daily_demand.groupby("Category Name")["quantity"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .index.tolist()
    )

    results = []

    for category in top_categories:
        try:
            plan = build_inventory_plan(
                daily_demand,
                category,
                lead_time_days=7,
                service_level=0.95
            )
            results.append(plan)

        except Exception as error:
            print(f"Error for {category}: {error}")
            continue

    return {"summary": results}
