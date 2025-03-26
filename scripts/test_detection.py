import yaml
import sys
import glob
import pandas as pd
from pyspark.sql import SparkSession
from pathlib import Path

def run_detection(app_name: str):

    config_path = list(Path(f"apps/{app_name}/base/config").glob("*.yaml"))
    if not config_path:
        print(f"❌ No detection YAML found in apps/{app_name}/base/config/")
        return

    with open(config_path[0], "r") as f:
        config = yaml.safe_load(f)

    return

    data_path = Path(f"apps/{app_name}/sample_data.csv")
    if not data_path.exists():
        print(f"❌ No sample_data.csv found at {data_path}")
        return

    df = spark.read.option("header", True).csv(str(data_path))
    df.createOrReplaceTempView("logs")

    # Example detection logic: failed login threshold
    threshold = config.get("threshold", 5)
    print(f"✅ Running detection with threshold: {threshold}")

    result = spark.sql(f"""
        SELECT user, COUNT(*) AS failed_attempts
        FROM logs
        WHERE status = 'fail'
        GROUP BY user
        HAVING failed_attempts > {threshold}
    """)

    result.show(truncate=False)

def find_valid_apps():
    apps_dir = Path("apps")
    return [
        app.name for app in apps_dir.iterdir()
        if (app / "base" / "config").exists()
        and any((app / "base" / "config").glob("*.yaml"))
    ]

if __name__ == "__main__":

    spark = SparkSession.builder \
        .appName(f"Test Detection app") \
        .getOrCreate()

    if len(sys.argv) == 2:
        app_name = sys.argv[1]
        run_detection(app_name)
    else:
        print("🔍 Running all valid apps...")
        for app_name in find_valid_apps():
            print(f"\n--- Running {app_name} ---")
            run_detection(app_name)
    
    spark.stop()
