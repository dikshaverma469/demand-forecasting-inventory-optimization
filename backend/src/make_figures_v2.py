import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
OUT = os.path.join(BASE, 'outputs')
FIG = os.path.join(BASE, 'figures')
os.makedirs(FIG, exist_ok=True)

pred = pd.read_csv(os.path.join(OUT, 'xgboost_predictions_v2.csv'), parse_dates=['order_date'])
res = pd.read_csv(os.path.join(OUT, 'model_comparison_v2.csv'))


def wape(a, p):
    return np.abs(a - p).sum() / a.sum() * 100


# Fig 1: WAPE by model
res = res.sort_values('test_wape', ascending=False)
fig, ax = plt.subplots(figsize=(8, 4.5))
colors = ['#d95f02' if 'XGBoost' in m else '#7570b3' if 'Moving' in m else '#999999'
          for m in res['model']]
bars = ax.barh(res['model'], res['test_wape'], color=colors)
for b, v in zip(bars, res['test_wape']):
    ax.text(v + 0.3, b.get_y() + b.get_height() / 2, f'{v:.1f}%', va='center')
ax.set_xlabel('Test WAPE (%) - lower is better')
ax.set_title('Forecast accuracy on the held-out test period (May-Sep 2017)')
plt.tight_layout()
plt.savefig(os.path.join(FIG, 'fig1_wape_by_model.png'), dpi=200)
plt.close()

# Fig 2: total daily demand, actual vs forecasts
daily = pred.groupby('order_date')[['quantity', 'ma30', 'xgb_ratio']].sum()
sm = daily.rolling(7, min_periods=1).mean()
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(sm.index, sm['quantity'], label='Actual', color='black', lw=2)
ax.plot(sm.index, sm['ma30'], label='30-day moving average', color='#7570b3')
ax.plot(sm.index, sm['xgb_ratio'], label='XGBoost (ratio target)', color='#d95f02')
ax.set_ylabel('Units per day (7-day smoothed, all categories)')
ax.set_title('Actual vs forecast, test period')
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG, 'fig2_actual_vs_forecast.png'), dpi=200)
plt.close()

# Fig 3: WAPE by category, MA30 vs XGBoost ratio
cat = (pred.groupby('Category Name')
       .apply(lambda g: pd.Series({'MA30': wape(g['quantity'], g['ma30']),
                                   'XGBoost ratio': wape(g['quantity'], g['xgb_ratio'])}),
              include_groups=False)
       .sort_values('MA30'))
x = np.arange(len(cat))
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(x - 0.2, cat['MA30'], 0.4, label='30-day MA', color='#7570b3')
ax.bar(x + 0.2, cat['XGBoost ratio'], 0.4, label='XGBoost ratio', color='#d95f02')
ax.set_xticks(x)
ax.set_xticklabels(cat.index, rotation=60, ha='right')
ax.set_ylabel('Test WAPE (%)')
ax.set_title('Accuracy by category')
ax.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIG, 'fig3_wape_by_category.png'), dpi=200)
plt.close()

print('Saved figures to', FIG)