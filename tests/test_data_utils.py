import pandas as pd

from data_utils import (
    convert_units,
    drop_invalid_required_rows,
    filter_to_timezone,
    parse_period_and_value,
    top_n_by_total,
)


def test_convert_units_to_gwh_creates_scaled_column():
    df = pd.DataFrame({"value": [1000.0, 2500.0]})
    converted, ycol, ylabel = convert_units(df, "GWh")
    assert ycol == "value_gwh"
    assert ylabel == "Demand (GWh)"
    assert converted["value_gwh"].tolist() == [1.0, 2.5]


def test_convert_units_to_mwh_keeps_original_column():
    df = pd.DataFrame({"value": [1000.0, 2500.0]})
    converted, ycol, ylabel = convert_units(df, "MWh")
    assert ycol == "value"
    assert ylabel == "Demand (MWh)"
    assert "value_gwh" not in converted.columns


def test_filter_to_timezone_only_keeps_matching_rows():
    df = pd.DataFrame(
        {
            "timezone": ["Eastern", "UTC", "eastern", "PACIFIC"],
            "value": [1, 2, 3, 4],
        }
    )
    filtered = filter_to_timezone(df, "eastern")
    assert filtered["value"].tolist() == [1, 3]


def test_filter_to_timezone_returns_input_when_column_missing():
    df = pd.DataFrame({"value": [1, 2, 3]})
    filtered = filter_to_timezone(df, "eastern")
    assert filtered.equals(df)


def test_top_n_by_total_keeps_only_largest_categories():
    df = pd.DataFrame(
        {
            "type-name": ["coal", "coal", "solar", "gas", "gas", "wind"],
            "Demand": [5, 5, 12, 7, 4, 1],
        }
    )
    filtered = top_n_by_total(df, "type-name", "Demand", top_n=2)
    assert set(filtered["type-name"].unique()) == {"solar", "gas"}
    assert filtered["Demand"].sum() == 23


def test_parse_period_and_value_converts_types():
    df = pd.DataFrame(
        {"period": ["2026-02-01", "not-a-date"], "value": ["12.5", "oops"]}
    )
    parsed = parse_period_and_value(df)
    assert parsed["period"].notna().sum() == 1
    assert parsed["value"].tolist()[0] == 12.5
    assert pd.isna(parsed["value"].tolist()[1])


def test_drop_invalid_required_rows_filters_null_required_fields():
    df = pd.DataFrame(
        {
            "period": [pd.Timestamp("2026-02-01"), pd.NaT],
            "value": [10.0, 20.0],
            "type_name": ["coal", "gas"],
        }
    )
    cleaned, warnings = drop_invalid_required_rows(
        df, required_columns=["period", "value", "type_name"]
    )

    assert len(cleaned) == 1
    assert cleaned["type_name"].tolist() == ["coal"]
    assert any("Dropped 1 invalid rows" in warning for warning in warnings)
