"""Spark Structured Streaming from Kafka into Bronze Delta.

Notes:
- Checkpoint location is non-negotiable — that's where offset state lives.
- `failOnDataLoss` defaults to true; only flip during a deliberate reset.
- `mergeSchema=true` lets new fields appear; pair with a drift alert.
"""

from pyspark.sql.functions import from_json, col, current_timestamp
from pyspark.sql.types import (
    StructType, StringType, LongType, TimestampType,
)


ORDER_SCHEMA = (
    StructType()
    .add("order_id", StringType())
    .add("customer_id", StringType())
    .add("revenue_cents", LongType())
    .add("event_time", TimestampType())
)


def stream_bronze_orders(spark, kafka_bootstrap: str, topic: str, bronze_path: str):
    raw = (
        spark.readStream
             .format("kafka")
             .option("kafka.bootstrap.servers", kafka_bootstrap)
             .option("subscribe", topic)
             .option("startingOffsets", "latest")
             .load()
    )

    parsed = (
        raw.select(
            from_json(col("value").cast("string"), ORDER_SCHEMA).alias("data"),
            col("timestamp").alias("_kafka_timestamp"),
            current_timestamp().alias("_ingested_at"),
        )
        .select("data.*", "_kafka_timestamp", "_ingested_at")
    )

    return (
        parsed.writeStream
              .format("delta")
              .outputMode("append")
              .option("checkpointLocation", f"{bronze_path}/_checkpoint")
              .option("mergeSchema", "true")
              .trigger(processingTime="30 seconds")
              .start(bronze_path)
    )
