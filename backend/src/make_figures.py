"""
Generates paper-ready figures and a metrics table from the project's own outputs.
Run from backend/src:   python make_figures.py
Writes to ../figures/ (PNG, 300 dpi) and ../figures/metrics.csv
"""
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

sys.path.append(os.path.dirname(__file__))
from features import build_features, encode_category

OUT = "../figures"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({
    "font.family": "serif", "font.size": 11, "axes.spines.top": False,
    "axes.spines.right": False, "savefig.dpi": 300, "figure.dpi": 100,
})
C = {"xgb": "#1f4e79", "naive": "#9a9a9a", "ma": "#2a9d8f", "prophet": "#e76f51", "actual": "#222222"}
rng = np.random.default_rng(42)

def wape(a, p):
    a, p = np.asarray(a, float), np.asarray(p, float)
    return np.abs(a - p).sum() / a.sum() * 100

def boot_ci(a, p, n=1000):
    a, p = np.asarray(a, float), np.asarray(p, float)
    idx = rng.integers(0, len(a), (n, len(a)))
    vals = np.abs(a[idx] - p[idx]).sum(1) / a[idx].sum(1) * 100
    return np.percentile(vals, [2.5, 97.5])

def save(name):
    plt.tight_layout(); plt.savefig(f"{OUT}/{name}.png", bbox_inches="tight"); plt.close()
    print("saved", name)

raw = pd.read_csv("../data/daily_demand_by_category.csv", parse_dates=["order_date"])
pred = pd.read_csv("../outputs/xgboost_predictions.csv", parse_dates=["order_date"])
pred["resid"] = pred["quantity"] - pred["xgb_pred"]
THRESH = 15

# Fig 1: effect of the quantity >= 15 training filter
top = raw.groupby("Category Name")["quantity"].sum().sort_values(ascending=False).head(15).index
t = raw[raw["Category Name"].isin(top)]
removed = (t["quantity"] < THRESH).mean() * 100
fig, ax = plt.subplots(figsize=(7, 4))
ax.hist(t["quantity"], bins=40, color="#8fa9c4", edgecolor="white")
ax.axvline(THRESH, color="#c0392b", ls="--", label=f"Filter threshold = {THRESH}")
ax.set(xlabel="Daily quantity per category", ylabel="Number of category-days",
       title=f"Old filter (quantity >= {THRESH}) removed {removed:.1f}% of category-days")
ax.legend(frameon=False); save("fig01_quantity_filter")

# Fig 2: predicted vs actual (density coloured)
xy = np.vstack([pred["quantity"], pred["xgb_pred"]])
dens = stats.gaussian_kde(xy)(xy)
fig, ax = plt.subplots(figsize=(5.5, 5))
sc = ax.scatter(pred["quantity"], pred["xgb_pred"], c=dens, s=10, cmap="viridis", alpha=.8)
lim = max(pred["quantity"].max(), pred["xgb_pred"].max()) * 1.05
ax.plot([0, lim], [0, lim], "r--", label="Perfect prediction")
ax.set(xlabel="Actual demand (units)", ylabel="Predicted demand (units)", xlim=(0, lim), ylim=(0, lim))
plt.colorbar(sc, label="Density"); ax.legend(frameon=False, loc="upper left"); save("fig02_pred_vs_actual")

# Fig 3: residual diagnostics
fig, axs = plt.subplots(1, 3, figsize=(13, 4))
axs[0].scatter(pred["xgb_pred"], pred["resid"], s=8, alpha=.4, color=C["xgb"])
axs[0].axhline(0, color="r", ls="--"); axs[0].set(xlabel="Fitted values", ylabel="Residual", title="(a) Residuals vs fitted")
axs[1].hist(pred["resid"], bins=40, density=True, color="#8fa9c4", edgecolor="white")
mu, sd = pred["resid"].mean(), pred["resid"].std()
xs = np.linspace(pred["resid"].min(), pred["resid"].max(), 200)
axs[1].plot(xs, stats.norm.pdf(xs, mu, sd), "r"); axs[1].set(xlabel="Residual", ylabel="Density",
       title=f"(b) Distribution (skew={stats.skew(pred['resid']):.2f})")
stats.probplot(pred["resid"], plot=axs[2]); axs[2].set_title("(c) Normal Q-Q plot")
save("fig03_residual_diagnostics")

# Fig 4: model comparison with bootstrap CIs (same rows for every model)
models = {"Naive (lag-1)": pred["lag_1"], "Seasonal naive (lag-7)": pred["lag_7"],
          "Moving avg (7-day)": pred["rolling_mean_7"], "Moving avg (30-day)": pred["rolling_mean_30"],
          "XGBoost (absolute)": pred["xgb_pred"], "XGBoost (ratio target)": pred["xgb_ratio_pred"]}
rows = []
for name, p in models.items():
    lo, hi = boot_ci(pred["quantity"], p)
    rows.append({"model": name, "WAPE_%": wape(pred["quantity"], p), "CI_low": lo, "CI_high": hi,
                 "MAE": np.abs(pred["quantity"] - p).mean(),
                 "RMSE": np.sqrt(((pred["quantity"] - p) ** 2).mean())})
met = pd.DataFrame(rows); met.to_csv(f"{OUT}/metrics.csv", index=False); print(met.round(2).to_string(index=False))
fig, ax = plt.subplots(figsize=(7, 3.8))
y = np.arange(len(met))[::-1]
cols = [C["naive"], C["naive"], C["ma"], C["ma"], C["xgb"], C["xgb"]]
ax.errorbar(met["WAPE_%"], y, xerr=[met["WAPE_%"] - met["CI_low"], met["CI_high"] - met["WAPE_%"]],
            fmt="none", ecolor="k", capsize=3, zorder=1)
ax.scatter(met["WAPE_%"], y, c=cols, s=80, zorder=2, marker="D")
ax.set_yticks(y); ax.set_yticklabels(met["model"]); ax.set_xlabel("WAPE (%) with 95% bootstrap CI")
ax.set_title("Model comparison on the same test rows (May-Sep 2017)"); save("fig04_model_comparison")

# Fig 5: WAPE per category, XGBoost vs 30-day moving average
g = []
for cat, d in pred.groupby("Category Name"):
    if len(d) >= 30:
        g.append({"cat": cat, "XGBoost": wape(d["quantity"], d["xgb_ratio_pred"]),
                  "Moving avg (30-day)": wape(d["quantity"], d["rolling_mean_30"]), "n": len(d)})
g = pd.DataFrame(g).sort_values("XGBoost")
fig, ax = plt.subplots(figsize=(8, 4.2)); w = .38; x = np.arange(len(g))
ax.bar(x - w/2, g["XGBoost"], w, label="XGBoost (ratio target)", color=C["xgb"])
ax.bar(x + w/2, g["Moving avg (30-day)"], w, label="Moving avg (30-day)", color=C["ma"])
ax.set_xticks(x); ax.set_xticklabels(g["cat"], rotation=35, ha="right"); ax.set_ylabel("WAPE (%)")
ax.set_title("WAPE by category (categories with >= 30 test rows)"); ax.legend(frameon=False); save("fig05_category_wape")

# Fig 6: actual vs forecasts over the test period (Camping & Hiking)
cat = "Camping & Hiking"
xg = pred[pred["Category Name"] == cat].sort_values("order_date")
fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(xg["order_date"], xg["quantity"], color=C["actual"], lw=1.1, label="Actual")
ax.plot(xg["order_date"], xg["rolling_mean_30"], color=C["ma"], lw=1.3, label="Moving avg (30-day)")
ax.plot(xg["order_date"], xg["xgb_ratio_pred"], color=C["xgb"], lw=1.3, label="XGBoost (ratio target)")
ax.set(xlabel="Date", ylabel="Daily demand (units)", title=f"Actual vs forecast: {cat} (test period)")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3); fig.autofmt_xdate(); save("fig06_forecast_timeseries")

# Fig 7: SHAP (absolute-feature model, computed on the test rows)
try:
    import json, shap, xgboost as xgb
    FEATS = json.load(open("../models/feature_cols.json"))
    model = xgb.XGBRegressor(); model.load_model("../models/xgboost_model.json")
    X = pred[FEATS].sample(n=min(2000, len(pred)), random_state=42)
    sv = shap.TreeExplainer(model).shap_values(X)
    shap.summary_plot(sv, X, feature_names=FEATS, show=False); save("fig07a_shap_beeswarm")
    shap.summary_plot(sv, X, feature_names=FEATS, plot_type="bar", show=False); save("fig07b_shap_bar")
    pd.DataFrame({"feature": FEATS, "mean_abs_shap": np.abs(sv).mean(0)}).sort_values(
        "mean_abs_shap", ascending=False).to_csv(f"{OUT}/shap_importance.csv", index=False)
except Exception as e:
    print("SHAP figure skipped:", e)

# Fig 8: inventory plan by category
inv = pd.read_csv("../outputs/inventory_plan.csv").sort_values("reorder_point", ascending=False)
fig, ax = plt.subplots(figsize=(9, 4.2)); x = np.arange(len(inv))
ax.bar(x - .2, inv["safety_stock"], .4, label="Safety stock", color=C["ma"])
ax.bar(x + .2, inv["reorder_point"], .4, label="Reorder point", color=C["xgb"])
ax.set_xticks(x); ax.set_xticklabels(inv["category"], rotation=45, ha="right"); ax.set_ylabel("Units")
ax.set_title("Inventory plan (lead time 7 days, service level 95%)"); ax.legend(frameon=False); save("fig08_inventory_plan")