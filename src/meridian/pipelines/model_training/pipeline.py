"""Model training pipeline (feature -> model)."""
from kedro.pipeline import Pipeline, node

from meridian.pipelines.model_training import nodes


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=nodes.split_train_test,
                inputs=["demand_features", "params:model_training"],
                outputs=["train_set", "test_set"],
                name="split_train_test_node",
                tags=["train"],
            ),
            node(
                func=nodes.build_feature_spec,
                inputs=["train_set", "params:model_training"],
                outputs="feature_spec",
                name="build_feature_spec_node",
                tags=["train"],
            ),
            node(
                func=nodes.train_demand_model,
                inputs=["train_set", "feature_spec", "params:model_training"],
                outputs="demand_model",
                name="train_demand_model_node",
                tags=["train", "model"],
            ),
            node(
                func=nodes.fit_elasticity,
                inputs=["price_elasticity_features", "params:model_training"],
                outputs=["elasticity_model", "elasticity_coefficients"],
                name="fit_elasticity_node",
                tags=["train", "price"],
            ),
        ]
    )
