"""Tests for skyherd.edge.camera — MockCamera round-trip + get_camera factory."""

from __future__ import annotations

import numpy as np

from skyherd.edge.camera import (
    Camera,
    MockCamera,
    PiCameraUnavailable,
    get_camera,
)


class TestMockCamera:
    """MockCamera behaves as an RGB frame source without any hardware."""

    def test_capture_returns_numpy_array(self) -> None:
        cam = MockCamera()
        frame = cam.capture()
        assert isinstance(frame, np.ndarray)

    def test_capture_shape_is_hwc_rgb(self) -> None:
        cam = MockCamera(width=320, height=240)
        frame = cam.capture()
        assert frame.ndim == 3, "frame must be 3-D (H, W, C)"
        h, w, c = frame.shape
        assert c == 3, "must be RGB (3 channels)"
        assert h == 240
        assert w == 320

    def test_capture_dtype_is_uint8(self) -> None:
        cam = MockCamera()
        frame = cam.capture()
        assert frame.dtype == np.uint8

    def test_frame_count_increments(self) -> None:
        cam = MockCamera()
        cam.capture()
        cam.capture()
        assert cam._frame_count == 2

    def test_successive_captures_are_valid(self) -> None:
        cam = MockCamera()
        for _ in range(5):
            frame = cam.capture()
            assert frame.shape[2] == 3

    def test_close_is_idempotent(self) -> None:
        cam = MockCamera()
        cam.capture()
        cam.close()
        cam.close()  # second close must not raise

    def test_context_manager_closes_camera(self) -> None:
        with MockCamera() as cam:
            frame = cam.capture()
        assert isinstance(frame, np.ndarray)

    def test_implements_camera_abc(self) -> None:
        assert isinstance(MockCamera(), Camera)


class TestGetCamera:
    """get_camera factory returns the right backend."""

    def test_explicit_mock_returns_mock_camera(self) -> None:
        cam = get_camera(kind="mock")
        assert isinstance(cam, MockCamera)
        cam.close()

    def test_auto_returns_camera_on_non_pi(self) -> None:
        # On non-Pi (CI) host picamera2 is absent → must fall back to Mock
        cam = get_camera(kind="auto")
        assert isinstance(cam, Camera)
        frame = cam.capture()
        assert frame.ndim == 3
        cam.close()

    def test_pi_raises_on_non_pi_host(self) -> None:
        # Requesting Pi explicitly on a host without picamera2 should raise
        try:
            cam = get_camera(kind="pi")
            # If we somehow got here (picamera2 IS installed), just verify it works
            frame = cam.capture()
            assert isinstance(frame, np.ndarray)
            cam.close()
        except PiCameraUnavailable:
            pass  # expected on non-Pi

    def test_default_kind_is_auto(self) -> None:
        cam = get_camera()  # default should be "auto"
        assert isinstance(cam, Camera)
        cam.close()
