"""Medallion patterns (Bronze → Silver → Gold) on Delta Lake.

Idempotent by construction. Adapt paths and PKs; do not copy verbatim.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, lit, row_number, desc
from pyspark.sql.window import Window
from delta.tables import DeltaTable


spark = (
    SparkSession.builder
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .getOrCreate()
)


# ─── Bronze: append-only raw ingest ─────────────────────────────────────────
def ingest_bronze(source_path: str, bronze_table: str, source_system: str) -> int:
    df = spark.read.format("json").load(source_path)
    df = (
        df.withColumn("_ingested_at", current_timestamp())
          .withColumn("_source_system", lit(source_system))
          .withColumn("_source_file", col("_metadata.file_path"))
    )
    (df.write.format("delta")
       .mode("append")
       .option("mergeSchema", "true")           # alert on drift, do not block
       .save(bronze_table))
    return df.count()


# ─── Silver: dedup + upsert via MERGE (idempotent) ──────────────────────────
def upsert_silver(bronze_table: str, silver_table: str, pk_cols: list[str]) -> None:
    source = spark.read.format("delta").load(bronze_table)

    # Keep newest record per PK.
    w = Window.partitionBy(*pk_cols).orderBy(desc("_ingested_at"))
    source = (source.withColumn("_rank", row_number().over(w))
                    .filter(col("_rank") == 1)
                    .drop("_rank"))

    if DeltaTable.isDeltaTable(spark, silver_table):
        target = DeltaTable.forPath(spark, silver_table)
        cond = " AND ".join(f"target.{c} = source.{c}" for c in pk_cols)
        (target.alias("target")
               .merge(source.alias("source"), cond)
               .whenMatchedUpdateAll()
               .whenNotMatchedInsertAll()
               .execute())
    else:
        source.write.format("delta").mode("overwrite").save(silver_table)


# ─── Gold: partition-scoped overwrite (idempotent per partition) ────────────
def refresh_gold_daily_revenue(silver_orders: str, gold_table: str, date: str) -> None:
    df = spark.read.format("delta").load(silver_orders)
    gold = (
        df.filter((col("status") == "completed") & (col("order_date") == date))
          .groupBy("order_date", "region", "product_category")
          .agg({"revenue": "sum", "order_id": "count"})
          .withColumnRenamed("sum(revenue)", "total_revenue")
          .withColumnRenamed("count(order_id)", "order_count")
          .withColumn("_refreshed_at", current_timestamp())
    )
    (gold.write.format("delta")
         .mode("overwrite")
         .option("replaceWhere", f"order_date = '{date}'")
         .save(gold_table))
