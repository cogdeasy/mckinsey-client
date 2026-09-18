"""Accuracy metrics as defined in the Nordfalk model transparency note.

WAPE is the headline number in the weekly pack. MAPE is reported alongside it
but only over weeks where actual units are at or above the threshold in
parameters_model_evaluation.yml: the client's slow movers otherwise produce
MAPEs in the hundreds and the pack becomes unreadable (NFK-MT-092).

Bias is signed and expressed as a share of actuals, positive meaning the
model over-forecasts. The replenishment team read it as "how much extra
stock did we ask for".
"""
import numpy as np
from sklearn.metrics import mean_squared_error


def wape(actual, forecast):
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    denominator = np.abs(actual).sum()
    if denominator == 0:
        return np.nan
    return float(np.abs(forecast - actual).sum() / denominator)


def mape(actual, forecast, min_actual=5):
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    mask = actual >= min_actual
    if mask.sum() == 0:
        return np.nan
    return float(np.mean(np.abs((forecast[mask] - actual[mask]) / actual[mask])))


def bias(actual, forecast):
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    denominator = actual.sum()
    if denominator == 0:
        return np.nan
    return float((forecast - actual).sum() / denominator)


def rmse(actual, forecast):
    return float(np.sqrt(mean_squared_error(actual, forecast)))


def forecast_value_add(actual, forecast, naive):
    """Improvement in WAPE over the client's current naive (last year) rule."""
    base = wape(actual, naive)
    if not base or np.isnan(base):
        return np.nan
    return float((base - wape(actual, forecast)) / base)


METRIC_FUNCTIONS = {
    "wape": wape,
    "mape": mape,
    "bias": bias,
    "rmse": rmse,
}


def compute(metric_names, actual, forecast, min_actual=5):
    out = {}
    for name in metric_names:
        function = METRIC_FUNCTIONS[name]
        if name == "mape":
            out[name] = function(actual, forecast, min_actual=min_actual)
        else:
            out[name] = function(actual, forecast)
    return out
