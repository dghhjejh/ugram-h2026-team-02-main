class S3Storage:
    def __init__(self, bucket: str) -> None:
        self.bucket = bucket

    def save(self, file_name: str, _content: bytes) -> str:
        # Save file to AWS S3
        return f"s3://{self.bucket}/{file_name}"
