import pandas as pd

from schemas import validate_fuel_raw, validate_parsed, validate_region_raw


def test_validate_fuel_raw_accepts_valid_data_and_extra_columns():
    df = pd.DataFrame(
        {
            "period": ["2026-02-01"],
            "value": ["12.5"],
            "timezone": ["eastern"],
            "type-name": ["coal"],
            "extra": ["ok"],
        }
    )
    cleaned, warnings = validate_fuel_raw(df)
    assert warnings == []
    assert len(cleaned) == 1
    assert "extra" in cleaned.columns


def test_validate_fuel_raw_missing_required_column_returns_empty():
    df = pd.DataFrame({"period": ["2026-02-01"], "value": ["12.5"]})
    cleaned, warnings = validate_fuel_raw(df)
    assert cleaned.empty
    assert any("missing required columns" in warning for warning in warnings)


def test_validate_region_raw_missing_respondent_returns_empty():
    df = pd.DataFrame(
        {"period": ["2026-02-01"], "value": ["12.5"], "timezone": ["eastern"]}
    )
    cleaned, warnings = validate_region_raw(df)
    assert cleaned.empty
    assert any("missing required columns" in warning for warning in warnings)


def test_validate_parsed_drops_invalid_rows_and_warns():
    raw = pd.DataFrame(
        {
            "period": [pd.Timestamp("2026-02-01"), pd.NaT],
            "value": [10.0, 20.0],
            "type-name": ["coal", "gas"],
        }
    )
    cleaned, warnings = validate_parsed(raw, required_columns=["period", "value", "type-name"])
    assert len(cleaned) == 1
    assert cleaned["type-name"].tolist() == ["coal"]
    assert any("dropped" in warning for warning in warnings)
