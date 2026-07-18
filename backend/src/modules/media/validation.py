import io
import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


class MediaValidationError(Exception):
    """The uploaded bytes are not a supported, safe image."""


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    mime_type: str
    extension: str
    width: int
    height: int
    original: bytes
    preview: bytes


_FORMATS = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


class ImageValidator:
    def __init__(self, *, max_pixels: int = 40_000_000, preview_edge: int = 1600) -> None:
        self._max_pixels = max_pixels
        self._preview_edge = preview_edge

    def validate(self, path: Path) -> ValidatedImage:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(path) as probe:
                    image_format = probe.format
                    probe.verify()
                if image_format not in _FORMATS:
                    raise MediaValidationError("Unsupported media type")
                with Image.open(path) as decoded:
                    self._check_dimensions(decoded.size)
                    decoded.load()
                    image = ImageOps.exif_transpose(decoded)
                    return self._process(image, image_format)
        except MediaValidationError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise MediaValidationError("Image dimensions exceed the configured limit") from exc
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise MediaValidationError("Image cannot be decoded") from exc

    def _process(self, image: Image.Image, image_format: str) -> ValidatedImage:
        width, height = image.size
        self._check_dimensions(image.size)
        clean = self._clean_copy(image, image_format)
        original = self._encode(clean, image_format)
        preview_image = clean.copy()
        preview_image.thumbnail((self._preview_edge, self._preview_edge))
        preview = self._encode(preview_image, "WEBP")
        mime_type, extension = _FORMATS[image_format]
        return ValidatedImage(
            mime_type=mime_type,
            extension=extension,
            width=width,
            height=height,
            original=original,
            preview=preview,
        )

    def _check_dimensions(self, size: tuple[int, int]) -> None:
        width, height = size
        if width <= 0 or height <= 0 or width * height > self._max_pixels:
            raise MediaValidationError("Image dimensions exceed the configured limit")

    @staticmethod
    def _clean_copy(image: Image.Image, image_format: str) -> Image.Image:
        if image_format == "JPEG":
            return image.convert("RGB")
        if image.mode not in {"RGB", "RGBA", "L", "LA"}:
            return image.convert("RGBA" if "transparency" in image.info else "RGB")
        return image.copy()

    @staticmethod
    def _encode(image: Image.Image, image_format: str) -> bytes:
        output = io.BytesIO()
        options: dict[str, object] = {"optimize": True}
        if image_format == "JPEG":
            options["quality"] = 90
        elif image_format == "WEBP":
            options["quality"] = 85
        image.save(output, format=image_format, **options)
        return output.getvalue()
