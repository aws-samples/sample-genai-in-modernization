"""
Image processing utilities for resizing, converting, and handling various image formats.

This module provides functions to resize images, convert them to base64 format,
and determine image types based on file extensions.
"""

import base64
from io import BytesIO

from PIL import Image


def resize_image(image_bytes, max_size_mb=3.75, max_width_px=8000, max_height_px=8000):
    """
    Resize an image if it exceeds specified size or dimension limits.

    Args:
        image_bytes: Raw image data in bytes
        max_size_mb: Maximum file size in megabytes (default: 3.75)
        max_width_px: Maximum width in pixels (default: 8000)
        max_height_px: Maximum height in pixels (default: 8000)

    Returns:
        bytes: Resized image data in PNG format
    """
    image = Image.open(BytesIO(image_bytes))

    # Check image size
    image_size = len(image_bytes) / (1024 * 1024)  # Convert bytes to MB
    image_width, image_height = image.size

    if (
        image_size > max_size_mb
        or image_width > max_width_px
        or image_height > max_height_px
    ):
        # Calculate resize ratio
        resize_ratio = min(max_width_px / image_width, max_height_px / image_height)
        new_size = (int(image_width * resize_ratio), int(image_height * resize_ratio))

        # Resize image using LANCZOS resampling
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Convert resized image to bytes
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return buffered.getvalue()


def convert_image_to_base64(image_bytes):
    """
    Convert image bytes to base64 encoded string.

    Args:
        image_bytes: Raw image data in bytes

    Returns:
        str: Base64 encoded image string
    """
    # Convert image to base64
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    return base64_image


def get_image_type(image_file_name):
    """
    Determine the MIME type of an image based on its file extension.

    Args:
        image_file_name: Name of the image file including extension

    Returns:
        str: MIME type of the image

    Raises:
        ValueError: If the image format is not supported
    """
    # Convert filename to lowercase to handle case-insensitive extensions
    filename_lower = image_file_name.lower()

    # Determine the image type based on the file extension
    if filename_lower.endswith(".png"):
        image_type = "image/png"
    elif filename_lower.endswith(".jpg") or filename_lower.endswith(".jpeg"):
        image_type = "image/jpeg"
    elif filename_lower.endswith(".webp"):
        image_type = "image/webp"
    elif filename_lower.endswith(".gif"):
        image_type = "image/gif"
    else:
        raise ValueError(
            "Only 'jpeg', 'png', 'webp', and 'gif' image formats are currently supported"
        )
    return image_type
