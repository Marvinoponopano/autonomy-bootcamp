"""FixedCamera: a finished camera example

Hand it a list of images and it gives them back one at a time. It exists to
make tests repeatable, and as your reference for Part 2. Read it with
``tests/test_fixed_camera.py``.

Worth stealing: the ``_initialized`` flag, ``_next_timestamp()``, and the
two ``.copy()`` calls.
"""

import time

import numpy as np

from .abstract_camera import AbstractCamera
from .frame import CameraFrame


class FixedCamera(AbstractCamera):
    """A camera that plays back a list of images you give it.

    Loops the list forever, so it behaves like any other camera: capture as
    long as it's on. ``index`` counts captures, not position in the list.

    Args:
        frames: A list, with at least one item, of ``(height, width, 3)``
            ``uint8`` numpy arrays. The camera keeps its own copies, so
            changing your arrays afterwards does nothing to it.

    Raises:
        TypeError: If ``frames`` isn't a list, or something in it isn't a
            numpy array.
        ValueError: If ``frames`` is empty, or an array isn't shaped
            ``(height, width, 3)`` with dtype ``uint8``.

    Example:
        >>> images = [np.zeros((4, 6, 3), dtype=np.uint8)]
        >>> camera = FixedCamera(images)
        >>> camera.initialize_camera()
        True
        >>> camera.capture_frame().index
        0
        >>> camera.capture_frame().index   # same image, next index
        1
        >>> camera.stop()
    """

    def __init__(self, frames: list[np.ndarray]) -> None:
        if not isinstance(frames, list):
            raise TypeError(f"frames must be a list, got {type(frames).__name__}")
        if not frames:
            raise ValueError("frames must not be empty")
        for position, frame in enumerate(frames):
            if not isinstance(frame, np.ndarray):
                raise TypeError(
                    f"frames[{position}] must be a numpy array, "
                    f"got {type(frame).__name__}"
                )
            if frame.ndim != 3 or frame.shape[2] != 3: # must be 3d array and 3 channels for RGB
                raise ValueError(
                    f"frames[{position}] must have shape (height, width, 3), "
                    f"got {frame.shape}"
                )
            if frame.dtype != np.uint8:
                raise ValueError(
                    f"frames[{position}] must have dtype uint8, got {frame.dtype}"
                )

        # Copy arugment frames
        self._frames = [frame.copy() for frame in frames]
        self._initialized = False
        self._captures = 0
        self._last_timestamp = float("-inf")

    def initialize_camera(self) -> bool:
        """Turn the camera on."""
        self._initialized = True
        self._captures = 0
        return True

    def capture_frame(self) -> CameraFrame:
        """Return the next stored image, looping back to the start at the end.

        Copies before handing the image over, so a caller drawing on the
        frame can't change what we give out next time.
        """
        if not self._initialized:
            raise RuntimeError(
                "capture_frame() called on a camera that is not initialized; "
                "call initialize_camera() first"
            )

        frame = CameraFrame(
            # Copy going out: whoever gets this can do what they want with it.
            rgb=self._frames[self._captures % len(self._frames)].copy(),
            timestamp=self._next_timestamp(),
            index=self._captures,
        )
        self._captures += 1
        return frame

    def stop(self) -> None:
        """Turn the camera off.

        One flag, no cleanup, so calling it twice or before starting is fine.
        Capturing raises from here on.
        """
        self._initialized = False

    def _next_timestamp(self) -> float:
        """Read the clock, making sure the number beats the last one.

        ``time.monotonic()`` can return the same value twice if you call it
        twice fast enough, which would break ordering, so nudge it up.
        """
        timestamp = time.monotonic()
        if timestamp <= self._last_timestamp:
            timestamp = self._last_timestamp + 1e-6
        self._last_timestamp = timestamp
        return timestamp
