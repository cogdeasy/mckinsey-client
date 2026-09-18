import numpy as np
import pytest

from meridian.pipelines.model_evaluation import metrics


def test_wape():
    actual = np.array([100.0, 200.0, 300.0])
    forecast = np.array([110.0, 180.0, 300.0])
    assert metrics.wape(actual, forecast) == pytest.approx(30.0 / 600.0)


def test_bias_is_signed():
    actual = np.array([100.0, 100.0])
    assert metrics.bias(actual, np.array([110.0, 110.0])) == pytest.approx(0.1)
    assert metrics.bias(actual, np.array([90.0, 90.0])) == pytest.approx(-0.1)


def test_mape_ignores_small_actuals():
    actual = np.array([1.0, 100.0])
    forecast = np.array([10.0, 110.0])
    # The 1 unit line would dominate; the client agreed a floor of 5 units.
    assert metrics.mape(actual, forecast) == pytest.approx(0.1)


def test_forecast_value_add_against_the_naive():
    actual = np.array([100.0, 100.0])
    forecast = np.array([105.0, 95.0])
    naive = np.array([120.0, 80.0])
    assert metrics.forecast_value_add(actual, forecast, naive) == pytest.approx(0.75)
