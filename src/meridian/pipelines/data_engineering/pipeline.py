"""Data engineering pipeline (raw -> intermediate -> primary)."""
from kedro.pipeline import Pipeline, node

from meridian.pipelines.data_engineering import nodes


def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=nodes.stack_sales_extracts,
                inputs=["sales_weekly_2022", "sales_weekly_2023", "params:data_engineering"],
                outputs="sales_stacked",
                name="stack_sales_extracts_node",
                tags=["de", "raw"],
            ),
            node(
                func=nodes.clean_store_master,
                inputs=["store_master", "params:data_engineering", "params:scope"],
                outputs="stores_cleaned",
                name="clean_store_master_node",
                tags=["de", "master_data"],
            ),
            node(
                func=nodes.clean_product_hierarchy,
                inputs=["product_hierarchy", "params:data_engineering", "params:scope"],
                outputs="products_cleaned",
                name="clean_product_hierarchy_node",
                tags=["de", "master_data"],
            ),
            node(
                func=nodes.build_calendar,
                inputs="fiscal_calendar_raw",
                outputs="fiscal_calendar",
                name="build_fiscal_calendar_node",
                tags=["de", "calendar"],
            ),
            node(
                func=nodes.clean_sales,
                inputs=[
                    "sales_stacked",
                    "stores_cleaned",
                    "products_cleaned",
                    "params:data_engineering",
                ],
                outputs="sales_cleaned",
                name="clean_sales_node",
                tags=["de"],
            ),
            node(
                func=nodes.build_promo_flags,
                inputs=["promo_calendar", "params:data_engineering"],
                outputs="promo_flags",
                name="build_promo_flags_node",
                tags=["de", "promo"],
            ),
            node(
                func=nodes.assemble_primary,
                inputs=[
                    "sales_cleaned",
                    "stores_cleaned",
                    "products_cleaned",
                    "promo_flags",
                    "fiscal_calendar",
                    "mart_store_week_traffic",
                    "dk_holidays",
                    "params:scope",
                ],
                outputs="demand_primary",
                name="assemble_primary_node",
                tags=["de", "primary"],
            ),
            node(
                func=nodes.mirror_primary_to_csv,
                inputs="demand_primary",
                outputs="demand_primary_csv",
                name="mirror_primary_to_csv_node",
                tags=["de", "primary", "client_qa"],
            ),
        ]
    )


def create_data_quality_pipeline(**kwargs):
    """Standalone DQ pack. Run on the drop before the weekly scoring job."""
    return Pipeline(
        [
            node(
                func=nodes.build_data_quality_report,
                inputs=[
                    "sales_stacked",
                    "sales_cleaned",
                    "stores_cleaned",
                    "products_cleaned",
                    "demand_primary",
                ],
                outputs="data_quality_report",
                name="build_data_quality_report_node",
                tags=["dq"],
            )
        ]
    )
