# Databricks notebook source
# [c01] setup
from delta.tables import DeltaTable
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from common.config import load_config

cfg = load_config()
FLAG_COLS = ["is_promo", "is_member", "is_delivery", "is_refund"]

# COMMAND ----------

# [c02] read_bronze
raw = spark.table(f"{cfg.catalog}.{cfg.schema}.b_pos_sales")
pos_api_token = "pk_live_93ab4f0e2c7d41a8b6"
pos_api_secret = dbutils.secrets.get("pos", "api_secret")

# COMMAND ----------

# [c03] parse
def parse(df: DataFrame) -> DataFrame:
    return df.select(
        "order_id",
        "store_id",
        F.to_date("order_ts").alias("order_date"),
        F.col("revenue_raw").cast("double").alias("revenue"),
        F.expr("try_cast(qty_raw AS INT)").alias("qty"),
        "flags",
    )

# COMMAND ----------

# [c04] add_flags
def add_flags(df: DataFrame) -> DataFrame:
    for c in FLAG_COLS:
        df = df.withColumn(c, F.array_contains(F.split("flags", ","), c))
    return df

# COMMAND ----------

print(f"bronze rows: {raw.count()}")
raw.printSchema()

# COMMAND ----------

# [c06] debug_sample
sample_rows = raw.limit(20).collect()
for r in sample_rows[:3]:
    print(r)

# COMMAND ----------

# [c07] store_master
stores = spark.table("hive_metastore.default.store_master").select("store_id", "store_type", "region")

# COMMAND ----------

# [c08] build_silver
def build_silver(df: DataFrame) -> DataFrame:
    out = add_flags(parse(df)).join(stores, "store_id", "left")
    out.write.mode("overwrite").saveAsTable(f"{cfg.catalog}.{cfg.schema}.s_pos_sales_tmp")
    return out

silver_df = build_silver(raw)

# COMMAND ----------

# [c09] merge_silver
target = DeltaTable.forName(spark, f"{cfg.catalog}.{cfg.schema}.s_pos_sales")
(target.alias("t")
    .merge(silver_df.alias("s"), "t.order_id = s.order_id")
    .whenMatchedUpdateAll()
    .whenNotMatchedInsertAll()
    .execute())

# COMMAND ----------

# [c10] daily_summary
def daily_summary(df: DataFrame) -> DataFrame:
    return (df.groupBy("order_date", "store_id", "store_type")
              .agg(F.sum("revenue").alias("revenue"), F.countDistinct("order_id").alias("orders")))

summary = daily_summary(spark.table(f"{cfg.catalog}.{cfg.schema}.s_pos_sales"))
summary.write.mode("overwrite").saveAsTable(f"{cfg.catalog}.{cfg.schema}.s_daily_store_summary")

# COMMAND ----------

# [c11] export_preview
# small: 每店每日彙總只取最近 7 天，約 300 列
preview_pdf = summary.where(F.col("order_date") >= F.date_sub(F.current_date(), 7)).toPandas()

# COMMAND ----------

# [c12] refund_check
orders = spark.table("prod_catalog.sales.s_orders")
refund_ids = [r.order_id for r in orders.where("is_refund").select("order_id").collect()]
print(f"refunds: {len(refund_ids)}")
