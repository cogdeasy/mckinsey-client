"""Data engineering node tests.

This is the pipeline the client's platform team review, so it carries the
bulk of the coverage.
"""
import pandas as pd
import pytest

from meridian.pipelines.data_engineering import nodes
from meridian.utils.validation import DataQualityError


def test_stack_sales_extracts_normalises_keys(sales_extract, de_params):
    stacked = nodes.stack_sales_extracts(sales_extract, sales_extract.head(0), de_params)

    assert len(stacked) == len(sales_extract)
    assert set(["store_id", "sku_id", "week_label", "units", "gross_value_dkk"]).issubset(
        stacked.columns
    )
    assert stacked["store_id"].map(len).eq(4).all()
    assert stacked["sku_id"].map(len).eq(5).all()
    assert stacked["week_label"].tolist()[0] == "202201"
    assert stacked["date"].dtype.kind == "M"


def test_stack_sales_extracts_requires_the_client_columns(sales_extract, de_params):
    broken = sales_extract.drop(columns=["omsaetning_dkk"])
    with pytest.raises(DataQualityError):
        nodes.stack_sales_extracts(broken, sales_extract, de_params)


def test_clean_store_master_drops_depots_test_and_franchise(
    store_master, store_params, scope_params
):
    stores = nodes.clean_store_master(store_master, store_params, scope_params)

    assert sorted(stores["store_id"]) == ["1101", "4201"]
    assert stores.loc[stores["store_id"] == "1101", "region_code"].iloc[0] == "11"
    assert stores.loc[stores["store_id"] == "1101", "region_name"].iloc[0] == "Hovedstaden"
    assert stores.loc[stores["store_id"] == "4201", "region_group"].iloc[0] == "STORBY"


def test_clean_store_master_drops_closed_stores(store_master, store_params, scope_params):
    stores = nodes.clean_store_master(store_master, store_params, scope_params)
    assert "6201" not in set(stores["store_id"])


def test_clean_store_master_keeps_closed_stores_when_configured(
    store_master, store_params, scope_params
):
    params = dict(store_params)
    params["drop_closed_stores"] = False
    stores = nodes.clean_store_master(store_master, params, scope_params)
    assert "6201" in set(stores["store_id"])


def test_clean_product_hierarchy_repoints_migrated_articles(
    product_hierarchy, product_params, scope_params
):
    products = nodes.clean_product_hierarchy(product_hierarchy, product_params, scope_params)

    repointed = products[products["sku_id"] == "12300"]
    assert repointed["category_code"].iloc[0] == "12"
    assert repointed["is_fresh"].iloc[0]


def test_clean_product_hierarchy_drops_internal_categories(
    product_hierarchy, product_params, scope_params
):
    products = nodes.clean_product_hierarchy(product_hierarchy, product_params, scope_params)
    assert "99001" not in set(products["sku_id"])
    assert products["case_pack"].min() >= 1


def test_clean_sales_strips_deposit_and_vat(
    sales_extract, store_master, product_hierarchy, de_params, store_params,
    product_params, scope_params,
):
    stacked = nodes.stack_sales_extracts(sales_extract, sales_extract.head(0), de_params)
    stores = nodes.clean_store_master(store_master, store_params, scope_params)
    products = nodes.clean_product_hierarchy(product_hierarchy, product_params, scope_params)

    sales = nodes.clean_sales(stacked, stores, products, de_params)

    soft_drink = sales[sales["sku_id"] == "20114"].iloc[0]
    expected_net = (1687.50 - 120 * 3.0) / 1.25
    assert soft_drink["net_value_dkk"] == pytest.approx(expected_net)
    assert soft_drink["unit_price_dkk"] == pytest.approx(expected_net / 120)

    milk = sales[(sales["sku_id"] == "10023") & (sales["store_id"] == "1101")].iloc[0]
    assert milk["net_value_dkk"] == pytest.approx(3918.75 / 1.25)


def test_clean_sales_drops_out_of_scope_stores(
    sales_extract, store_master, product_hierarchy, de_params, store_params,
    product_params, scope_params,
):
    stacked = nodes.stack_sales_extracts(sales_extract, sales_extract.head(0), de_params)
    stores = nodes.clean_store_master(store_master, store_params, scope_params)
    products = nodes.clean_product_hierarchy(product_hierarchy, product_params, scope_params)

    sales = nodes.clean_sales(stacked, stores, products, de_params)

    assert "9001" not in set(sales["store_id"])


def test_clean_sales_zeroes_returns_by_default(
    sales_extract, store_master, product_hierarchy, de_params, store_params,
    product_params, scope_params,
):
    stacked = nodes.stack_sales_extracts(sales_extract, sales_extract.head(0), de_params)
    stores = nodes.clean_store_master(store_master, store_params, scope_params)
    products = nodes.clean_product_hierarchy(product_hierarchy, product_params, scope_params)

    sales = nodes.clean_sales(stacked, stores, products, de_params)

    assert sales["units"].min() >= 0


def test_clean_sales_can_drop_returns(
    sales_extract, store_master, product_hierarchy, de_params, store_params,
    product_params, scope_params,
):
    params = dict(de_params)
    params["outliers"] = dict(de_params["outliers"])
    params["outliers"]["negative_units_policy"] = "drop"

    stacked = nodes.stack_sales_extracts(sales_extract, sales_extract.head(0), params)
    stores = nodes.clean_store_master(store_master, store_params, scope_params)
    products = nodes.clean_product_hierarchy(product_hierarchy, product_params, scope_params)

    sales = nodes.clean_sales(stacked, stores, products, params)

    assert "202202" not in set(sales["week_label"])


def test_clean_sales_flags_promotions(
    sales_extract, store_master, product_hierarchy, de_params, store_params,
    product_params, scope_params,
):
    stacked = nodes.stack_sales_extracts(sales_extract, sales_extract.head(0), de_params)
    stores = nodes.clean_store_master(store_master, store_params, scope_params)
    products = nodes.clean_product_hierarchy(product_hierarchy, product_params, scope_params)

    sales = nodes.clean_sales(stacked, stores, products, de_params)

    leaflet = sales[sales["sku_id"] == "10047"].iloc[0]
    assert leaflet["promo_flag"] == 1
    assert leaflet["promo_weight"] == 1.0
    assert sales["promo_flag"].sum() == 1


def test_build_promo_flags_explodes_multi_week_campaigns(promo_calendar, de_params):
    flags = nodes.build_promo_flags(promo_calendar, de_params)

    leaflet = flags[flags["sku_id"] == "10047"]
    assert len(leaflet) == 1
    assert leaflet["week_label"].iloc[0] == "202201"
    assert leaflet["discount_depth"].iloc[0] == pytest.approx(0.25)
    assert leaflet["is_leaflet"].iloc[0] == 1

    jutland = flags[flags["sku_id"] == "20114"]
    assert sorted(jutland["week_label"]) == ["202201", "202202"]
    assert set(jutland["store_group"]) == {"JYLLAND"}
    assert jutland["is_leaflet"].max() == 0


def test_build_promo_flags_on_an_empty_calendar(promo_calendar, de_params):
    flags = nodes.build_promo_flags(promo_calendar.head(0), de_params)
    assert flags.empty


def test_build_calendar(fiscal_calendar_raw):
    calendar = nodes.build_calendar(fiscal_calendar_raw)
    assert calendar["week_label"].is_unique
    assert "is_period_end" in calendar.columns


def test_assemble_primary_is_unique_on_the_primary_keys(
    sales_extract, store_master, product_hierarchy, promo_calendar, fiscal_calendar_raw,
    holidays_extract, traffic, de_params, store_params, product_params, scope_params,
):
    stacked = nodes.stack_sales_extracts(sales_extract, sales_extract.head(0), de_params)
    stores = nodes.clean_store_master(store_master, store_params, scope_params)
    products = nodes.clean_product_hierarchy(product_hierarchy, product_params, scope_params)
    sales = nodes.clean_sales(stacked, stores, products, de_params)
    flags = nodes.build_promo_flags(promo_calendar, de_params)
    calendar = nodes.build_calendar(fiscal_calendar_raw)

    primary = nodes.assemble_primary(
        sales, stores, products, flags, calendar, traffic, holidays_extract, scope_params
    )

    assert not primary.duplicated(subset=nodes.PRIMARY_KEYS).any()
    assert primary["store_traffic"].notnull().any()
    assert primary["fiscal_period"].notnull().all()

    promoted = primary[primary["sku_id"] == "10047"].iloc[0]
    assert promoted["discount_depth"] == pytest.approx(0.25)


def test_assemble_primary_raises_on_duplicate_keys(
    sales_extract, store_master, product_hierarchy, promo_calendar, fiscal_calendar_raw,
    holidays_extract, traffic, de_params, store_params, product_params, scope_params,
):
    stacked = nodes.stack_sales_extracts(sales_extract, sales_extract.head(0), de_params)
    stores = nodes.clean_store_master(store_master, store_params, scope_params)
    products = nodes.clean_product_hierarchy(product_hierarchy, product_params, scope_params)
    sales = nodes.clean_sales(stacked, stores, products, de_params)
    duplicated = pd.concat([sales, sales.head(1)], ignore_index=True)
    flags = nodes.build_promo_flags(promo_calendar, de_params)
    calendar = nodes.build_calendar(fiscal_calendar_raw)

    with pytest.raises(DataQualityError):
        nodes.assemble_primary(
            duplicated, stores, products, flags, calendar, traffic, holidays_extract,
            scope_params,
        )
