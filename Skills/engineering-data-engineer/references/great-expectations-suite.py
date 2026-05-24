"""Validation harness — wire to fail the pipeline run on critical-suite failure.

Pattern: read the dataframe, run the expectation suite, raise on failure.
Non-critical suites can warn instead of raise.
"""

from datetime import datetime
import great_expectations as gx


class DataQualityException(RuntimeError):
    pass


def validate_silver_orders(df) -> dict:
    context = gx.get_context()
    batch = context.sources.pandas_default.read_dataframe(df)

    result = batch.validate(
        expectation_suite_name="silver_orders.critical",
        run_id={
            "run_name": "silver_orders_daily",
            "run_time": datetime.utcnow(),
        },
    )

    stats = {
        "success": result["success"],
        "evaluated": result["statistics"]["evaluated_expectations"],
        "passed": result["statistics"]["successful_expectations"],
        "failed": result["statistics"]["unsuccessful_expectations"],
    }

    if not result["success"]:
        raise DataQualityException(
            f"silver_orders failed validation: {stats['failed']} checks failed"
        )
    return stats
