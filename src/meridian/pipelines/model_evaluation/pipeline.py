"""Model evaluation pipeline (model -> accuracy pack)."""
from kedro.pipeline import Pipeline, node

from meridian.pipelines.model_evaluation import nodes


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=nodes.score_test_set,
                inputs=["test_set", "demand_model", "feature_spec"],
                outputs="test_predictions",
                name="score_test_set_node",
                tags=["eval"],
            ),
            node(
                func=nodes.accuracy_by_region,
                inputs=["test_predictions", "params:model_evaluation"],
                outputs="accuracy_by_region",
                name="accuracy_by_region_node",
                tags=["eval", "pack"],
            ),
            node(
                func=nodes.accuracy_by_category,
                inputs=["test_predictions", "params:model_evaluation"],
                outputs="accuracy_by_category",
                name="accuracy_by_category_node",
                tags=["eval", "pack"],
            ),
            node(
                func=nodes.rolling_backtest,
                inputs=[
                    "demand_features",
                    "demand_model",
                    "feature_spec",
                    "params:model_evaluation",
                    "params:model_training",
                ],
                outputs="backtest_summary",
                name="rolling_backtest_node",
                tags=["eval", "backtest"],
            ),
            node(
                func=nodes.feature_importance,
                inputs=["demand_model", "feature_spec", "params:model_evaluation"],
                outputs="feature_importance",
                name="feature_importance_node",
                tags=["eval"],
            ),
        ]
    )
