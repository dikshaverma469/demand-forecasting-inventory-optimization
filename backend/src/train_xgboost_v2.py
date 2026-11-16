import os
import sys

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from features_v2 import complete_calendar, build_features_v2, CAT, DATE, TARGET

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)                       # demand-forecast/
DATA = os.path.join(BASE, 'data', 'daily_demand_by_category.csv')
OUT = os.path.join(BASE, 'outputs')
MODELS = os.path.join(BASE, 'models')

TRAIN_END = pd.Timestamp('2016-12-31')
VAL_END = pd.Timestamp('2017-04-30')
TEST_END = pd.Timestamp('2017-09-30')

ABS_COLS = [
    'Category Name_code', 'day_of_week', 'is_weekend', 'month', 'week_of_year',
    'lag_1', 'lag_7', 'lag_14', 'rolling_mean_7', 'rolling_mean_30',
    'avg_discount_rate_prev', 'late_delivery_risk_prev',
]
REL_COLS = [
    'Category Name_code', 'day_of_week', 'is_weekend', 'month', 'week_of_year',
    'lag_1_rel', 'lag_7_rel', 'lag_14_rel', 'rolling_mean_7_rel',
    'avg_discount_rate_prev', 'late_delivery_risk_prev',
]


def wape(actual, pred):
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    return np.abs(actual - pred).sum() / actual.sum() * 100


def fit_xgb(Xtr, ytr, Xv, yv, depth):
    m = xgb.XGBRegressor(
        n_estimators=1000, max_depth=depth, learning_rate=0.03,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        random_state=42, early_stopping_rounds=50,
    )
    m.fit(Xtr, ytr, eval_set=[(Xv, yv)], verbose=False)   # validation only
    return m


def main():
    raw = pd.read_csv(DATA, parse_dates=[DATE])

    # Top 15 categories by volume (same as before)
    top = raw.groupby(CAT)[TARGET].sum().sort_values(ascending=False).head(15).index
    raw = raw[raw[CAT].isin(top)]

    df, cut = complete_calendar(raw)
    if cut:
        print('Discontinued categories (data stops at last sale, no fake zeros):')
        for c, d in cut.items():
            print(f'   {c}: last sale {d.date()}')

    df = build_features_v2(df)
    df = df[df[DATE] <= TEST_END]

    need = list(dict.fromkeys(ABS_COLS + REL_COLS + ['rolling_mean_30', 'lag_1', 'lag_7',
                                                     'rolling_mean_7', 'base', 'target_ratio']))
    df = df.dropna(subset=need + [TARGET])

    train = df[df[DATE] <= TRAIN_END]
    val = df[(df[DATE] > TRAIN_END) & (df[DATE] <= VAL_END)]
    test = df[(df[DATE] > VAL_END) & (df[DATE] <= TEST_END)]
    print(f'\nRows  train={len(train)}  val={len(val)}  test={len(test)}')
    if min(len(train), len(val), len(test)) == 0:
        raise SystemExit('One split is empty - check the date ranges against your data.')

    # ---- Absolute-target XGBoost (depth chosen on validation only)
    best_abs, best_abs_w = None, 1e9
    for depth in [2, 3, 4]:
        m = fit_xgb(train[ABS_COLS], train[TARGET], val[ABS_COLS], val[TARGET], depth)
        w = wape(val[TARGET], m.predict(val[ABS_COLS]))
        print(f'  abs   depth={depth}  val WAPE={w:.2f}%')
        if w < best_abs_w:
            best_abs, best_abs_w = m, w

    # ---- Ratio-target XGBoost: predict demand / recent level
    best_rel, best_rel_w = None, 1e9
    for depth in [2, 3, 4]:
        m = fit_xgb(train[REL_COLS], train['target_ratio'],
                    val[REL_COLS], val['target_ratio'], depth)
        pred_units = m.predict(val[REL_COLS]) * val['base']
        w = wape(val[TARGET], pred_units)
        print(f'  ratio depth={depth}  val WAPE={w:.2f}%')
        if w < best_rel_w:
            best_rel, best_rel_w = m, w

    # ---- Test predictions (test period touched only here)
    out = test[[CAT, DATE, TARGET]].copy()
    out['naive_lag1'] = test['lag_1']
    out['naive_lag7'] = test['lag_7']
    out['ma7'] = test['rolling_mean_7']
    out['ma30'] = test['rolling_mean_30']
    out['xgb_abs'] = np.clip(best_abs.predict(test[ABS_COLS]), 0, None)
    out['xgb_ratio'] = np.clip(best_rel.predict(test[REL_COLS]), 0, None) * test['base']

    names = {
        'naive_lag1': 'Naive (lag-1)',
        'naive_lag7': 'Seasonal naive (lag-7)',
        'ma7': 'Moving average (7-day)',
        'xgb_abs': 'XGBoost, absolute features',
        'xgb_ratio': 'XGBoost, ratio target',
        'ma30': 'Moving average (30-day)',
    }
    rows = [(names[k], wape(out[TARGET], out[k])) for k in names]
    res = pd.DataFrame(rows, columns=['model', 'test_wape']).sort_values('test_wape', ascending=False)

    print('\n=== Test WAPE (May-Sep 2017) ===')
    print(res.to_string(index=False, float_format=lambda x: f'{x:.1f}'))

    os.makedirs(OUT, exist_ok=True)
    os.makedirs(MODELS, exist_ok=True)
    out.to_csv(os.path.join(OUT, 'xgboost_predictions_v2.csv'), index=False)
    res.to_csv(os.path.join(OUT, 'model_comparison_v2.csv'), index=False)
    best_abs.save_model(os.path.join(MODELS, 'xgboost_model_v2_abs.json'))
    best_rel.save_model(os.path.join(MODELS, 'xgboost_model_v2_ratio.json'))
    joblib.dump({'abs_cols': ABS_COLS, 'rel_cols': REL_COLS},
                os.path.join(MODELS, 'xgboost_v2_features.pkl'))
    print('\nSaved v2 files (old outputs/models were NOT overwritten).')


if __name__ == '__main__':
    main()