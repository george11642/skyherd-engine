"""Camera abstraction — PiCamera (hardware) or MockCamera (CI / non-Pi)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger(__name__)

# Frame dimensions shared by both backends
_FRAME_WIDTH = 640
_FRAME_HEIGHT = 480


class CameraError(Exception):
    """Base exception for all camera errors."""


class PiCameraUnavailable(CameraError):
    """Raised when picamera2 is not installed or /dev/video0 is absent."""


class Camera(ABC):
    """Abstract camera.  Concrete implementations must be context-manager safe."""

    @abstractmethod
    def capture(self) -> np.ndarray:
        """Return one RGB frame as a numpy array of shape (H, W, 3), dtype uint8."""

    @abstractmethod
    def close(self) -> None:
        """Release hardware / file resources."""

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> Camera:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class PiCamera(Camera):
    """Raspberry Pi camera via picamera2 (BSD-2-Clause).

    Lazy-imports ``picamera2`` so the module can be imported on non-Pi hosts
    without error — the exception is raised only when PiCamera is instantiated.

    Raises
    ------
    PiCameraUnavailable
        If ``picamera2`` is not installed or the camera device is absent.
    """

    def __init__(
        self,
        width: int = _FRAME_WIDTH,
        height: int = _FRAME_HEIGHT,
    ) -> None:
        try:
            from picamera2 import Picamera2  # type: ignore[import-untyped]
        except ImportError as exc:
            raise PiCameraUnavailable(
                "picamera2 not installed — run: sudo apt install python3-picamera2 "
                "and ensure /dev/video0 exists"
            ) from exc

        self._cam = Picamera2()
        cfg = self._cam.create_still_configuration(
            main={"size": (width, height), "format": "RGB888"}
        )
        self._cam.configure(cfg)
        self._cam.start()
        logger.info("PiCamera started (%dx%d)", width, height)

    def capture(self) -> np.ndarray:
        """Capture and return an RGB frame."""
        frame: np.ndarray = self._cam.capture_array()
        return frame

    def close(self) -> None:
        """Stop and close the camera."""
        try:
            self._cam.stop()
            self._cam.close()
        except Exception:  # noqa: BLE001
            pass
        logger.info("PiCamera closed")


class MockCamera(Camera):
    """CI-safe mock camera that produces deterministic synthetic frames.

    Uses ``skyherd.vision.renderer`` when available, otherwise falls back to
    a solid-colour numpy array so tests never require a GUI or Pi hardware.
    """

    def __init__(
        self,
        width: int = _FRAME_WIDTH,
        height: int = _FRAME_HEIGHT,
    ) -> None:
        self._width = width
        self._height = height
        self._frame_count = 0

    def capture(self) -> np.ndarray:
        """Return a synthetic RGB frame."""
        self._frame_count += 1
        # Attempt rich render; fall back to a simple gradient array
        try:
            from PIL import Image, ImageDraw  # type: ignore[import-untyped]

            img = Image.new("RGB", (self._width, self._height), color=(34, 85, 34))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), f"MockCamera frame={self._frame_count}", fill=(255, 255, 255))
            arr: np.ndarray = np.array(img, dtype=np.uint8)
            return arr
        except ImportError:
            # Fallback: solid green frame
            return np.full((self._height, self._width, 3), [34, 85, 34], dtype=np.uint8)

    def close(self) -> None:
        logger.debug("MockCamera closed after %d frames", self._frame_count)


def get_camera(kind: str = "auto") -> Camera:
    """Camera factory.

    Parameters
    ----------
    kind:
        ``"pi"``   — always try PiCamera; raise if unavailable.
        ``"mock"`` — always return MockCamera.
        ``"auto"`` — try PiCamera; silently fall back to MockCamera.

    Returns
    -------
    Camera
        An initialised camera ready for ``.capture()`` calls.
    """
    if kind == "mock":
        logger.info("Camera: MockCamera (explicit)")
        return MockCamera()

    if kind == "pi":
        cam = PiCamera()
        logger.info("Camera: PiCamera (explicit)")
        return cam

    # auto
    try:
        cam = PiCamera()
        logger.info("Camera: PiCamera (auto-detected)")
        return cam
    except (PiCameraUnavailable, Exception):  # noqa: BLE001
        logger.info("Camera: MockCamera (PiCamera unavailable — using mock)")
        return MockCamera()
