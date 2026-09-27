from unittest.mock import patch

import pytest
from src.domain.images.image_processor import (
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_PIXELS,
    ImageProcessor,
)


class FakeImage:
    def __init__(self, size: tuple[int, int]) -> None:
        self.size = size
        self.mode = "RGB"

    def load(self) -> None:
        return None


def test_process_image_rejects_images_with_dimension_over_limit() -> None:
    processor = ImageProcessor()
    image_bytes = b"fake-image-bytes"

    with patch("src.domain.images.image_processor.PILImage.open", return_value=FakeImage((MAX_IMAGE_DIMENSION + 1, 1))):
        with pytest.raises(ValueError, match="Image exceeds safe size limits"):
            processor.process_image(image_bytes)


def test_process_image_rejects_images_with_pixel_count_over_limit() -> None:
    processor = ImageProcessor()
    width = 8_000
    height = (MAX_IMAGE_PIXELS // width) + 1
    image_bytes = b"fake-image-bytes"

    with patch("src.domain.images.image_processor.PILImage.open", return_value=FakeImage((width, height))):
        with pytest.raises(ValueError, match="Image exceeds safe size limits"):
            processor.process_image(image_bytes)
