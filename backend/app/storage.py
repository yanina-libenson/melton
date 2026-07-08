"""Cloudflare R2 (S3-compatible) file storage client."""

import boto3

from app.config import settings


def get_r2_client():
    """Return a boto3 S3 client configured for Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def upload_file(filename: str, content: bytes, content_type: str) -> str:
    """Upload file content to R2 and return its public URL."""
    client = get_r2_client()
    client.put_object(
        Bucket=settings.r2_bucket_name,
        Key=filename,
        Body=content,
        ContentType=content_type,
    )
    return f"{settings.r2_public_url}/{filename}"
