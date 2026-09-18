"""Pipeline registry.

Short names are what the delivery team and the Control-M jobs use:

    kedro run --pipeline de        raw -> intermediate -> primary
    kedro run --pipeline fe        primary -> features
    kedro run --pipeline train     features -> model
    kedro run --pipeline eval      model -> accuracy pack
    kedro run --pipeline scoring   model -> 13 week forecast + hand-off file

`__default__` is the training path only. The scoring run is scheduled
separately (NFK_MERIDIAN_SCORE_W) and must not be pulled into the default
pipeline: it would re-score on the training split.
"""
from meridian.pipelines import data_engineering as de
from meridian.pipelines import feature_engineering as fe
from meridian.pipelines import model_evaluation as ev
from meridian.pipelines import model_training as mt
from meridian.pipelines import scoring as sc


def register_pipelines():
    data_engineering = de.create_pipeline()
    feature_engineering = fe.create_pipeline()
    model_training = mt.create_pipeline()
    model_evaluation = ev.create_pipeline()
    scoring = sc.create_pipeline()
    data_quality = de.create_data_quality_pipeline()

    training_path = (
        data_engineering + feature_engineering + model_training + model_evaluation
    )

    return {
        "de": data_engineering,
        "data_engineering": data_engineering,
        "dq": data_quality,
        "fe": feature_engineering,
        "feature_engineering": feature_engineering,
        "train": model_training,
        "model_training": model_training,
        "eval": model_evaluation,
        "model_evaluation": model_evaluation,
        "scoring": scoring,
        "weekly": data_engineering + feature_engineering + scoring,
        "__default__": training_path,
    }
