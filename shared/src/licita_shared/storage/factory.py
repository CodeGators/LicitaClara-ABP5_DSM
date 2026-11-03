from licita_shared.storage.local import LocalObjectStorage


def storage(settings):
    if settings.storage_backend == "local":
        return LocalObjectStorage(settings.storage_root)
    import boto3
    from botocore.config import Config

    from licita_shared.storage.s3 import S3ObjectStorage

    client = boto3.client(
        "s3",
        endpoint_url=settings.object_storage_endpoint,
        aws_access_key_id=settings.object_storage_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.object_storage_secret_access_key.get_secret_value(),
        config=Config(
            signature_version="s3v4",
            connect_timeout=10,
            read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
    return S3ObjectStorage(settings.object_storage_bucket, client)
