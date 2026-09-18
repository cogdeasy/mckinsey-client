"""Scoring pipeline (model -> 13 week forecast + client hand-off)."""
from kedro.pipeline import Pipeline, node

from meridian.pipelines.scoring import nodes


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=nodes.build_scoring_frame,
                inputs=["demand_features", "promo_flags", "params:scoring"],
                outputs="scoring_frame",
                name="build_scoring_frame_node",
                tags=["scoring"],
            ),
            node(
                func=nodes.score_forecast,
                inputs=["scoring_frame", "demand_model", "feature_spec"],
                outputs="forecast_raw",
                name="score_forecast_node",
                tags=["scoring"],
            ),
            node(
                func=nodes.apply_business_rules,
                inputs=["forecast_raw", "params:scoring"],
                outputs="forecast_adjusted",
                name="apply_business_rules_node",
                tags=["scoring", "business_rules"],
            ),
            node(
                func=nodes.run_scenarios,
                inputs=[
                    "scoring_frame",
                    "demand_model",
                    "feature_spec",
                    "elasticity_model",
                    "params:scoring",
                ],
                outputs="scenario_results",
                name="run_scenarios_node",
                tags=["scoring", "scenarios"],
            ),
            node(
                func=nodes.build_export,
                inputs=["forecast_adjusted", "params:scoring"],
                outputs="forecast_export",
                name="export_forecast_node",
                tags=["scoring", "handoff"],
            ),
            node(
                func=nodes.summarise_forecast,
                inputs="forecast_adjusted",
                outputs="forecast_summary",
                name="summarise_forecast_node",
                tags=["scoring", "pack"],
            ),
        ]
    )
