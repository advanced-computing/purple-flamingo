from __future__ import annotations

from typing import Iterable

import pandas as pd
import pandera.pandas as pa


FUEL_RAW_SCHEMA = pa.DataFrameSchema(
    {
        "period": pa.Column(str, nullable=False),
        "value": pa.Column(object, nullable=False),
        "timezone": pa.Column(str, nullable=True),
        "type-name": pa.Column(str, nullable=False),
    },
    coerce=False,
    strict=False,
)

REGION_RAW_SCHEMA = pa.DataFrameSchema(
    {
        "period": pa.Column(str, nullable=False),
        "value": pa.Column(object, nullable=False),
        "timezone": pa.Column(str, nullable=True),
        "respondent": pa.Column(str, nullable=False),
    },
    coerce=False,
    strict=False,
)

PARSED_SCHEMA = pa.DataFrameSchema(
    {
        "period": pa.Column(pa.DateTime, nullable=True),
        "value": pa.Column(float, nullable=True, coerce=True),
    },
    strict=False,
)

DAILY_TOTALS_SCHEMA = pa.DataFrameSchema(
    {
        "period": pa.Column(pa.DateTime, nullable=False),
        "total_demand": pa.Column(
            float, nullable=False, coerce=True, checks=pa.Check.ge(0)
        ),
    },
    strict=False,
)

ANOMALY_SCHEMA = pa.DataFrameSchema(
    {
        "period": pa.Column(pa.DateTime, nullable=False),
        "total_demand": pa.Column(float, nullable=False, coerce=True),
        "demand_zscore": pa.Column(float, nullable=False, coerce=True),
        "anomaly_type": pa.Column(
            str, nullable=True, checks=pa.Check.isin(["high", "low"])
        ),
    },
    strict=False,
)

DAY_OVER_DAY_SCHEMA = pa.DataFrameSchema(
    {
        "period": pa.Column(pa.DateTime, nullable=False),
        "total_demand": pa.Column(float, nullable=False, coerce=True),
        "demand_change": pa.Column(float, nullable=True, coerce=True),
        "demand_pct_change": pa.Column(float, nullable=True, coerce=True),
    },
    strict=False,
)

FUEL_SHARE_SCHEMA = pa.DataFrameSchema(
    {
        "period": pa.Column(pa.DateTime, nullable=False),
        "type-name": pa.Column(str, nullable=False),
        "value": pa.Column(float, nullable=False, coerce=True),
        "share_pct": pa.Column(
            float,
            nullable=False,
            coerce=True,
            checks=[pa.Check.ge(0), pa.Check.le(100)],
        ),
    },
    strict=False,
)

MIX_COMPARISON_SCHEMA = pa.DataFrameSchema(
    {
        "day_type": pa.Column(str, nullable=False),
        "type-name": pa.Column(str, nullable=False),
        "avg_share_pct": pa.Column(
            float,
            nullable=False,
            coerce=True,
            checks=[pa.Check.ge(0), pa.Check.le(100)],
        ),
    },
    strict=False,
)


def _failure_preview(exc: pa.errors.SchemaErrors, limit: int = 5) -> str:
    failures = exc.failure_cases
    if failures.empty:
        return "no failure cases available"
    preview = failures.loc[:, ["column", "check", "failure_case"]].head(limit)
    return preview.to_dict(orient="records").__str__()


def _validate_and_clean(
    df: pd.DataFrame,
    schema: pa.DataFrameSchema,
    schema_name: str,
    required_columns: Iterable[str],
) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    try:
        validated = schema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as exc:
        warnings.append(f"{schema_name} validation warning: {_failure_preview(exc)}")
        validated = df.copy()
    except pa.errors.SchemaError as exc:
        warnings.append(f"{schema_name} validation warning: {exc}")
        validated = df.copy()

    missing = [col for col in required_columns if col not in validated.columns]
    if missing:
        warnings.append(f"{schema_name} missing required columns: {', '.join(missing)}")
        return pd.DataFrame(), warnings

    cleaned = validated.dropna(subset=list(required_columns)).copy()
    dropped_rows = len(validated) - len(cleaned)
    if dropped_rows > 0:
        warnings.append(
            f"{schema_name} dropped {dropped_rows} invalid rows with null required fields."
        )
    return cleaned, warnings


def validate_fuel_raw(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    return _validate_and_clean(
        df=df,
        schema=FUEL_RAW_SCHEMA,
        schema_name="Fuel raw schema",
        required_columns=["period", "value", "type-name"],
    )


def validate_region_raw(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    return _validate_and_clean(
        df=df,
        schema=REGION_RAW_SCHEMA,
        schema_name="Region raw schema",
        required_columns=["period", "value", "respondent"],
    )


def validate_parsed(
    df: pd.DataFrame, required_columns: Iterable[str]
) -> tuple[pd.DataFrame, list[str]]:
    return _validate_and_clean(
        df=df,
        schema=PARSED_SCHEMA,
        schema_name="Parsed schema",
        required_columns=required_columns,
    )


def validate_daily_totals(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    return _validate_and_clean(
        df=df,
        schema=DAILY_TOTALS_SCHEMA,
        schema_name="Daily totals schema",
        required_columns=["period", "total_demand"],
    )


def validate_anomaly(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    return _validate_and_clean(
        df=df,
        schema=ANOMALY_SCHEMA,
        schema_name="Anomaly schema",
        required_columns=["period", "total_demand", "demand_zscore", "anomaly_type"],
    )


def validate_day_over_day(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    return _validate_and_clean(
        df=df,
        schema=DAY_OVER_DAY_SCHEMA,
        schema_name="Day-over-day schema",
        required_columns=[
            "period",
            "total_demand",
            "demand_change",
            "demand_pct_change",
        ],
    )


def validate_fuel_share(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    return _validate_and_clean(
        df=df,
        schema=FUEL_SHARE_SCHEMA,
        schema_name="Fuel share schema",
        required_columns=["period", "type-name", "value", "share_pct"],
    )


def validate_mix_comparison(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    return _validate_and_clean(
        df=df,
        schema=MIX_COMPARISON_SCHEMA,
        schema_name="Mix comparison schema",
        required_columns=["day_type", "type-name", "avg_share_pct"],
    )
