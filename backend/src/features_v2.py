import numpy as np
import pandas as pd

CAT = 'Category Name'
DATE = 'order_date'
TARGET = 'quantity'

# These describe the SAME day's orders, so they are unknown before forecasting
# that day. We only ever use yesterday's value.
SAME_DAY_COLS = ['avg_discount_rate', 'late_delivery_risk']


def complete_calendar(df, gap_days=14):
    """
    One row per (category, day).
    - Days with no orders become zero demand.
    - A category whose last sale is more than `gap_days` before the end of the
      data is treated as discontinued: we stop at its last sale date instead of
      padding fake zeros after it.
    Returns (dataframe, {category: last_sale_date for cut categories}).
    """
    df = df.copy()
    df[DATE] = pd.to_datetime(df[DATE])
    global_end = df[DATE].max()

    agg = {TARGET: 'sum'}
    agg.update({c: 'mean' for c in SAME_DAY_COLS if c in df.columns})

    parts, cut = [], {}
    for cat, g in df.groupby(CAT):
        g = g.groupby(DATE).agg(agg).sort_index()
        last = g.index.max()
        end = global_end if (global_end - last).days <= gap_days else last
        if end != global_end:
            cut[cat] = last
        full = pd.date_range(g.index.min(), end, freq='D')
        g = g.reindex(full)
        g.index.name = DATE
        g[TARGET] = g[TARGET].fillna(0)
        g[CAT] = cat
        parts.append(g.reset_index())
    return pd.concat(parts, ignore_index=True), cut


def build_features_v2(df):
    df = df.sort_values([CAT, DATE]).copy()

    # Calendar
    df['month'] = df[DATE].dt.month
    df['day_of_week'] = df[DATE].dt.dayofweek
    df['week_of_year'] = df[DATE].dt.isocalendar().week.astype(int)
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    grp = df.groupby(CAT)[TARGET]

    # Lags and rolling means (always shifted, so only past days are used)
    for lag in [1, 7, 14, 30]:
        df[f'lag_{lag}'] = grp.shift(lag)
    for w in [7, 30]:
        df[f'rolling_mean_{w}'] = grp.transform(lambda s: s.shift(1).rolling(w).mean())

    # Same-day inputs -> yesterday's value (carry forward over zero-order days)
    for c in SAME_DAY_COLS:
        if c in df.columns:
            df[f'{c}_prev'] = df.groupby(CAT)[c].transform(lambda s: s.shift(1).ffill())

    # Ratio-target version: demand relative to the recent level
    df['base'] = df['rolling_mean_30'] + 1.0
    df['target_ratio'] = df[TARGET] / df['base']
    for c in ['lag_1', 'lag_7', 'lag_14', 'lag_30', 'rolling_mean_7']:
        df[f'{c}_rel'] = df[c] / df['base']

    df['Category Name_code'] = df[CAT].astype('category').cat.codes
    return df