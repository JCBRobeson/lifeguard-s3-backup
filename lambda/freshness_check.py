import os
from datetime import datetime, timezone

import boto3

s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET = os.environ["BUCKET"]
TOPIC_ARN = os.environ["TOPIC_ARN"]
EXPECTED = os.environ["EXPECTED"].split(",")
MAX_AGE_HOURS = float(os.environ.get("MAX_AGE_HOURS", "26"))


def lambda_handler(event, context):
    now = datetime.now(timezone.utc)

    found = {}
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET):
        for obj in page.get("Contents", []):
            found[obj["Key"]] = obj["LastModified"]
            print("Last Modified", found[obj["Key"]], obj["Key"])
    problems = []
    for key in EXPECTED:
        if key not in found:
            problems.append(f"{key}: missing")
            continue
        age_hours = (now - found[key]).total_seconds() / 3600
        print(f"Age: {age_hours:.1f} hours of {MAX_AGE_HOURS} hours for {key}")
        if age_hours > MAX_AGE_HOURS:
            problems.append(f"{key}: {age_hours:.1f} hours old")

    if problems:
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject="Home lab backup check FAILED",
            Message="These backups are missing or stale:\n\n" + "\n".join(problems),
        )
        print("ALERT sent:", problems)
    else:
        print("all backups fresh")

    return {"problems": problems}