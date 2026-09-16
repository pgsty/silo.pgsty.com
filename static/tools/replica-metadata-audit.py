#!/usr/bin/env python3
"""Read-only, exact-version Content-Encoding inventory for SILO (Python 3 + boto3)."""

import argparse
import collections
import datetime
import hashlib
import json
import re
import sys


def emit(record):
    print(json.dumps(record, ensure_ascii=True, default=str), flush=True)


def classify(value):
    """Classify the header only; this never establishes a safe object repair."""
    if value is None:
        return "unaffected-header", None, "encoding header absent"
    tokens = [part.strip(" \t") for part in value.split(",")]
    if (any(not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", t) for t in tokens)
            or len(set(t.lower() for t in tokens)) != len(tokens)):
        return "ambiguous", None, "malformed or repeated encoding tokens"
    if "aws-chunked" not in [t.lower() for t in tokens]:
        return "unaffected-header", None, "transport encoding token absent"
    if "aws-chunked" not in tokens:
        return "ambiguous", None, "noncanonical transport encoding spelling"
    remaining = [t for t in tokens if t != "aws-chunked"]
    return "confirmed-header", ", ".join(remaining) or None, "raw bytes require separate verification"


def inventory(client, bucket, prefix, site):
    from botocore.exceptions import BotoCoreError, ClientError

    pages = client.get_paginator("list_object_versions").paginate(Bucket=bucket, Prefix=prefix)
    for page in pages:
        for marker in page.get("DeleteMarkers", []):
            yield {"kind": "version", "site": site, "bucket": bucket, "key": marker["Key"],
                   "version_id": marker["VersionId"], "is_latest_at_listing": marker["IsLatest"],
                   "classification": "delete-marker", "listed_modified": marker["LastModified"]}
        for version in page.get("Versions", []):
            row = {"kind": "version", "site": site, "bucket": bucket, "key": version["Key"],
                   "version_id": version["VersionId"], "is_latest_at_listing": version["IsLatest"],
                   "listed_modified": version["LastModified"], "listed_etag": version["ETag"],
                   "listed_size": version["Size"]}
            try:
                head = client.head_object(Bucket=bucket, Key=version["Key"], VersionId=version["VersionId"])
            except (ClientError, BotoCoreError) as error:
                # Never emit request headers, credentials, SSE-C keys or arbitrary error bodies.
                row.update(classification="ambiguous", reason="exact-version HEAD failed",
                           error_code=(error.response.get("Error", {}).get("Code", "unknown")
                                       if isinstance(error, ClientError) else type(error).__name__))
                yield row
                continue
            encoding = head.get("ContentEncoding")
            classification, proposed, reason = classify(encoding)
            # Unversioned/null objects may omit x-amz-version-id. No other omission is accepted.
            returned_id = head.get("VersionId", "null")
            # HTTP Last-Modified has second precision; LIST XML may include fractions.
            modified = head.get("LastModified")
            if (returned_id != version["VersionId"] or head.get("ETag") != version["ETag"]
                    or head.get("ContentLength") != version["Size"]
                    or modified is None
                    or modified.replace(microsecond=0) != version["LastModified"].replace(microsecond=0)):
                classification, proposed, reason = "ambiguous", None, "LIST/HEAD identity or state changed"
            # Fingerprint metadata for conflict detection; do not export user metadata values.
            private_metadata = {k: v for k, v in head.items() if k != "ResponseMetadata"}
            fingerprint = hashlib.sha256(json.dumps(private_metadata, sort_keys=True, default=str).encode()).hexdigest()
            row.update(classification=classification, reason=reason, content_encoding=encoding,
                       proposed_content_encoding=proposed, metadata_sha256=fingerprint,
                       replication_status=head.get("ReplicationStatus"),
                       encryption=head.get("ServerSideEncryption"),
                       object_lock_mode=head.get("ObjectLockMode"),
                       retain_until=head.get("ObjectLockRetainUntilDate"),
                       legal_hold=head.get("ObjectLockLegalHoldStatus"))
            yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint-url", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--site", required=True, help="operator label; no credentials")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--profile", help="AWS shared-config profile with read-only credentials")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError

    client = boto3.Session(profile_name=args.profile).client(
        "s3", endpoint_url=args.endpoint_url, region_name=args.region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      connect_timeout=10, read_timeout=30, retries={"mode": "standard", "max_attempts": 3}))
    emit({"kind": "start", "schema": 1, "site": args.site, "bucket": args.bucket,
          "prefix": args.prefix, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "boto3": boto3.__version__, "scope": "header inventory; no object writes or body reads"})
    counts = collections.Counter()
    try:
        for row in inventory(client, args.bucket, args.prefix, args.site):
            counts[row["classification"]] += 1
            emit(row)
    except (ClientError, BotoCoreError) as error:
        emit({"kind": "summary", "listing_complete": False, "counts": counts,
              "error_type": type(error).__name__})
        return 1
    emit({"kind": "summary", "listing_complete": True, "counts": counts,
          "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    # Ambiguous rows require follow-up; a successful listing is not an all-clear.
    return 2 if counts["ambiguous"] else 0


if __name__ == "__main__":
    sys.exit(main())
