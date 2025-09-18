import os, re, time
import boto3 #type: ignore
from mcp.server.fastmcp import FastMCP # type: ignore
from dotenv import load_dotenv #type: ignore
load_dotenv()

REGION    = os.getenv("AWS_REGION", "eu-central-1")
WORKGROUP = os.getenv("ATHENA_WORKGROUP", "primary")
RESULT_S3 = os.getenv("ATHENA_OUTPUT_S3")
if not RESULT_S3:
    raise RuntimeError("ATHENA_OUTPUT_S3 is not set.")

SQL_BLOCK = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|MSCK|GRANT|REVOKE)\b", re.I)

athena = boto3.client("athena", region_name=REGION)
s3     = boto3.client("s3", region_name=REGION)

mcp = FastMCP("aws-data")

@mcp.tool()
def athena_query(sql: str) -> dict:
    """Run SELECT/EXPLAIN in Athena; returns QueryExecutionId."""
    if SQL_BLOCK.search(sql):
        raise ValueError("Only SELECT/EXPLAIN allowed.")
    resp = athena.start_query_execution(
        QueryString=sql,
        WorkGroup=WORKGROUP,
        ResultConfiguration={"OutputLocation": RESULT_S3},
    )
    return {"query_execution_id": resp["QueryExecutionId"]}

# add at top (already have most imports)
from typing import Optional

@mcp.tool()
def athena_results(
    query_execution_id: Optional[str] = None,
    queryExecutionId: Optional[str] = None,
    max_rows: int = 1000,
    wait_ms: int = 400,
    max_wait_s: int = 60,
) -> dict:
    """Poll until SUCCEEDED, then fetch up to max_rows."""
    qid = query_execution_id or queryExecutionId
    if not qid:
        raise ValueError("Provide query_execution_id (or queryExecutionId).")

    import time as _t
    start = _t.time()
    while True:
        q = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
        st = q["Status"]["State"]
        if st == "SUCCEEDED":
            break
        if st in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Athena {st}: {q['Status'].get('StateChangeReason','')}")
        if _t.time() - start > max_wait_s:
            raise TimeoutError("Athena query timed out")
        _t.sleep(wait_ms/1000)

    res = athena.get_query_results(QueryExecutionId=qid, MaxResults=max_rows)
    rows = res["ResultSet"]["Rows"]
    headers = [c.get("VarCharValue","") for c in rows[0]["Data"]] if rows else []
    data = [[d.get("VarCharValue", None) for d in r["Data"]] for r in rows[1:]] if len(rows) > 1 else []
    return {"columns": headers, "rows": data}

@mcp.tool()
def athena_status(
    query_execution_id: Optional[str] = None,
    queryExecutionId: Optional[str] = None,
) -> dict:
    qid = query_execution_id or queryExecutionId
    if not qid:
        raise ValueError("Provide query_execution_id (or queryExecutionId).")
    q = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]
    return {
        "state": q["Status"]["State"],
        "output_location": q["ResultConfiguration"]["OutputLocation"]
    }
# at top you already have: glue = boto3.client("glue", region_name=REGION)
glue = boto3.client("glue", region_name=REGION)

@mcp.tool()
def glue_list_databases(max_databases: int = 200) -> dict:
    """
    Return Glue database names.
    Set max_databases to cap the result size.
    """
    paginator = glue.get_paginator("get_databases")
    names, truncated = [], False
    for page in paginator.paginate():
        for db in page.get("DatabaseList", []):
            names.append(db["Name"])
            if len(names) >= max_databases:
                truncated = True
                return {"databases": names, "truncated": truncated}
    return {"databases": names, "truncated": truncated}


@mcp.tool()
def glue_list_tables(database: str, max_tables: int = 200, include_schema: bool = True) -> dict:
    """List tables in a Glue database, optionally with columns."""
    paginator = glue.get_paginator("get_tables")
    tables = []
    count = 0
    for page in paginator.paginate(DatabaseName=database):
        for t in page["TableList"]:
            item = {"table": t["Name"]}
            if include_schema:
                cols  = [{"name": c["Name"], "type": c["Type"]} for c in t["StorageDescriptor"]["Columns"]]
                parts = [{"name": p["Name"], "type": p["Type"]} for p in t.get("PartitionKeys", [])]
                item["columns"] = cols
                item["partitions"] = parts
            tables.append(item)
            count += 1
            if count >= max_tables:
                return {"database": database, "tables": tables, "truncated": True}
    return {"database": database, "tables": tables, "truncated": False}

@mcp.tool()
def athena_result_csv(query_execution_id: str, max_bytes: int | None = 2_000_000, encoding: str = "utf-8") -> dict:
    """
    Read the Athena result CSV from S3 and return it as text.
    max_bytes=None reads the whole object (be careful with very large results).
    """
    q = athena.get_query_execution(QueryExecutionId=query_execution_id)["QueryExecution"]
    out = q["ResultConfiguration"]["OutputLocation"]  # s3://bucket/key.csv
    assert out.startswith("s3://"), f"Unexpected output location: {out}"
    path = out[len("s3://"):]
    bucket, key = path.split("/", 1)

    # HEAD to know the size
    h = s3.head_object(Bucket=bucket, Key=key)
    total = int(h["ContentLength"])

    # Optionally read a byte range
    get_kwargs = {"Bucket": bucket, "Key": key}
    if isinstance(max_bytes, int) and max_bytes > 0 and max_bytes < total:
        get_kwargs["Range"] = f"bytes=0-{max_bytes-1}"
        truncated = True
    else:
        truncated = False

    obj = s3.get_object(**get_kwargs)
    data = obj["Body"].read()
    try:
        text = data.decode(encoding, errors="replace")
    except Exception:
        text = data.decode("utf-8", errors="replace")

    return {
        "bucket": bucket,
        "key": key,
        "content_length": total,
        "truncated": truncated,
        "csv": text,
    }

@mcp.tool()
def glue_table_schema(database: str, table: str) -> dict:
    """Return schema for a specific Glue table."""
    t = glue.get_table(DatabaseName=database, Name=table)["Table"]
    cols  = [{"name": c["Name"], "type": c["Type"]} for c in t["StorageDescriptor"]["Columns"]]
    parts = [{"name": p["Name"], "type": p["Type"]} for p in t.get("PartitionKeys", [])]
    return {"database": database, "table": table, "columns": cols, "partitions": parts}

@mcp.tool()
def s3_presign(bucket: str, key: str, expires_s: int = 3600) -> dict:
    """Return a presigned URL for the result file or any S3 object."""
    url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_s)
    return {"url": url, "expires_seconds": expires_s}

if __name__ == "__main__":
    mcp.run()  # <-- correct place for this line
