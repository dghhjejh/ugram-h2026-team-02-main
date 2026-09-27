"""Image processing service for resizing and format conversion."""

import warnings
from enum import Enum
from io import BytesIO

from PIL import Image as PILImage
from PIL import ImageOps

MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_DIMENSION = 10_000

PILImage.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class ImageFormat(str, Enum):
    """Available image format variants."""

    ORIGINAL = "original"
    THUMBNAIL = "thumbnail"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ImageDimensions:
    """Dimensions for each image format."""

    FORMATS = {
        ImageFormat.THUMBNAIL: (512, 512),
        ImageFormat.SMALL: (400, 400),
        ImageFormat.MEDIUM: (800, 800),
        ImageFormat.LARGE: (1600, 1600),
    }


class ImageProcessor:
    """Process and resize images to multiple formats."""

    def __init__(self, output_format: str = "JPEG", quality: int = 90) -> None:
        self.output_format = output_format
        self.quality = quality

    def process_image(self, image_input: bytes | PILImage.Image) -> dict[ImageFormat, bytes]:
        """Process image and return resized versions for all formats."""
        original_image = self._normalize_image_input(image_input)

        result: dict[ImageFormat, bytes] = {ImageFormat.ORIGINAL: self._encode_image(original_image)}
        for format_type, (width, height) in ImageDimensions.FORMATS.items():
            if format_type == ImageFormat.THUMBNAIL:
                resized = self._resize_image_square_cover(original_image, width, height)
            else:
                resized = self._resize_image(original_image, width, height)
            result[format_type] = self._encode_image(resized)

        return result

    def crop_image(
        self,
        image_bytes: bytes,
        *,
        aspect_ratio: float,
        zoom: float = 1.0,
        center_x_percent: float = 50.0,
        center_y_percent: float = 50.0,
    ) -> PILImage.Image:
        """Apply an Instagram-like crop before generating image formats."""
        if aspect_ratio <= 0:
            raise ValueError("aspect_ratio must be greater than 0")

        zoom = max(1.0, zoom)
        center_x_percent = min(max(center_x_percent, 0.0), 100.0)
        center_y_percent = min(max(center_y_percent, 0.0), 100.0)

        image = self._normalize_image_input(image_bytes)

        width, height = image.size
        image_ratio = width / height if height else 1.0

        if image_ratio > aspect_ratio:
            base_crop_height = height
            base_crop_width = int(round(base_crop_height * aspect_ratio))
        else:
            base_crop_width = width
            base_crop_height = int(round(base_crop_width / aspect_ratio))

        crop_width = max(1, min(width, int(round(base_crop_width / zoom))))
        crop_height = max(1, min(height, int(round(base_crop_height / zoom))))

        center_x = int(round((center_x_percent / 100.0) * width))
        center_y = int(round((center_y_percent / 100.0) * height))

        left = center_x - crop_width // 2
        top = center_y - crop_height // 2
        left = max(0, min(left, width - crop_width))
        top = max(0, min(top, height - crop_height))
        right = left + crop_width
        bottom = top + crop_height

        return image.crop((left, top, right, bottom))

    def _normalize_image_input(self, image_input: bytes | PILImage.Image) -> PILImage.Image:
        if isinstance(image_input, PILImage.Image):
            image = image_input
        else:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", PILImage.DecompressionBombWarning)
                    image = PILImage.open(BytesIO(image_input))
                    image.load()
            except (PILImage.DecompressionBombWarning, PILImage.DecompressionBombError) as exc:
                raise ValueError(
                    f"Image exceeds safe size limits (max {MAX_IMAGE_DIMENSION}px per side, max {MAX_IMAGE_PIXELS} pixels)",
                ) from exc
            except Exception as exc:
                raise ValueError(f"Failed to open image: {str(exc)}") from exc

        self._validate_image_size(image)

        if image.mode in ("RGBA", "LA", "P"):
            rgb_image = PILImage.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            return rgb_image

        return image

    def _validate_image_size(self, image: PILImage.Image) -> None:
        width, height = image.size
        if width <= 0 or height <= 0:
            raise ValueError("Invalid image dimensions")

        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            raise ValueError(
                f"Image exceeds safe size limits (max {MAX_IMAGE_DIMENSION}px per side, max {MAX_IMAGE_PIXELS} pixels)",
            )

        if width * height > MAX_IMAGE_PIXELS:
            raise ValueError(
                f"Image exceeds safe size limits (max {MAX_IMAGE_DIMENSION}px per side, max {MAX_IMAGE_PIXELS} pixels)",
            )

    def _resize_image(self, image: PILImage.Image, width: int, height: int) -> PILImage.Image:
        """Resize image maintaining aspect ratio without adding canvas padding."""
        resized_source = image.copy()
        resized_source.thumbnail((width, height), PILImage.Resampling.LANCZOS)
        return resized_source

    def _resize_image_square_cover(self, image: PILImage.Image, width: int, height: int) -> PILImage.Image:
        """Resize image to square by filling container with centered crop (no blur)."""
        return ImageOps.fit(image, (width, height), method=PILImage.Resampling.LANCZOS, centering=(0.5, 0.5))

    def _encode_image(self, image: PILImage.Image) -> bytes:
        """Encode image to bytes."""
        output = BytesIO()
        if self.output_format == "JPEG":
            image = image.convert("RGB")
            image.save(
                output,
                format=self.output_format,
                quality=self.quality,
                optimize=True,
                progressive=True,
            )
        elif self.output_format == "WEBP":
            image.save(output, format=self.output_format, quality=self.quality)
        else:
            image.save(output, format=self.output_format)

        return output.getvalue()
