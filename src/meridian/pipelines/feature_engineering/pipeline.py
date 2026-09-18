"""Feature engineering pipeline (primary -> feature)."""
from kedro.pipeline import Pipeline, node

from meridian.pipelines.feature_engineering import nodes


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=nodes.build_panel,
                inputs=["demand_primary", "params:feature_engineering"],
                outputs="demand_panel",
                name="build_panel_node",
                tags=["fe"],
            ),
            node(
                func=nodes.add_lag_features,
                inputs=["demand_panel", "params:feature_engineering"],
                outputs="demand_with_lags",
                name="add_lag_features_node",
                tags=["fe", "lags"],
            ),
            node(
                func=nodes.add_promo_features,
                inputs=["demand_with_lags", "params:feature_engineering"],
                outputs="demand_with_promo",
                name="add_promo_features_node",
                tags=["fe", "promo"],
            ),
            node(
                func=nodes.add_calendar_features,
                inputs=["demand_with_promo", "params:feature_engineering"],
                outputs="demand_with_calendar",
                name="add_calendar_features_node",
                tags=["fe", "calendar"],
            ),
            node(
                func=nodes.add_price_features,
                inputs=["demand_with_calendar", "price_history", "params:feature_engineering"],
                outputs="demand_with_price",
                name="add_price_features_node",
                tags=["fe", "price"],
            ),
            node(
                func=nodes.encode_categoricals,
                inputs=["demand_with_price", "params:feature_engineering"],
                outputs="demand_encoded",
                name="encode_categoricals_node",
                tags=["fe"],
            ),
            node(
                func=nodes.finalise_features,
                inputs=["demand_encoded", "params:feature_engineering"],
                outputs="demand_features",
                name="finalise_features_node",
                tags=["fe"],
            ),
            node(
                func=nodes.build_elasticity_frame,
                inputs=[
                    "demand_features",
                    "mart_promo_performance",
                    "params:feature_engineering",
                ],
                outputs="price_elasticity_features",
                name="build_elasticity_frame_node",
                tags=["fe", "price"],
            ),
        ]
    )
