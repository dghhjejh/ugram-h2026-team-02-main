class LocalStorage:
    def __init__(self, base_path: str) -> None:
        self.base_path = base_path

    def save(self, file_name: str, _content: bytes) -> str:
        # Save file to local disk
        return f"{self.base_path}/{file_name}"
