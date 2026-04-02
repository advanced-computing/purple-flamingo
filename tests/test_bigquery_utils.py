from bigquery_utils import get_bigquery_config


def test_get_bigquery_config_includes_default_region_table():
    config = get_bigquery_config({"gcp_service_account": {"project_id": "demo-project"}})

    assert config["project_id"] == "demo-project"
    assert config["dataset_id"] == "eia_data"
    assert config["fuel_table_id"] == "daily_fuel_main"
    assert config["region_table_id"] == "daily_region_main"


def test_get_bigquery_config_allows_region_table_override():
    config = get_bigquery_config(
        {
            "bigquery": {
                "project_id": "demo-project",
                "dataset_id": "demo_dataset",
                "fuel_table_id": "fuel_table",
                "region_table_id": "region_table",
            }
        }
    )

    assert config == {
        "project_id": "demo-project",
        "dataset_id": "demo_dataset",
        "fuel_table_id": "fuel_table",
        "region_table_id": "region_table",
    }
