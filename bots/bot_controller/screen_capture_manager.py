import logging
import time

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ScreenCaptureManager:
    """Lezat fork: stills of the meeting while someone shares their screen.

    Off until the API turns it on (someone typed "NoteZat capturar" in the
    chat). While on, not paused and someone is sharing, it takes a screenshot
    of the meeting every ``interval_seconds`` and keeps it unless it shows the
    same thing as the last one kept (a slide nobody changed).
    """

    # Stills are scaled down to this width: enough to read a slide.
    MAX_WIDTH = 1600
    JPEG_QUALITY = 80
    # Two captures show the same thing when under this share of the pixels of
    # their 160x90 grayscale thumbnails changed visibly (a new slide number or
    # line of text is ~1%).
    THUMBNAIL_SIZE = (160, 90)
    CHANGED_PIXEL_DELTA = 25
    SAME_IMAGE_MAX_CHANGED_SHARE = 0.003

    def __init__(self, *, take_screenshot_callback, save_capture_callback, is_paused_callback, interval_seconds=15):
        self.take_screenshot_callback = take_screenshot_callback
        self.save_capture_callback = save_capture_callback
        self.is_paused_callback = is_paused_callback
        self.interval_seconds = interval_seconds
        self.enabled = False
        self.screen_sharers = set()
        self.last_capture_attempt_at = None
        self.last_thumbnail = None

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        # The first capture after turning on happens right away.
        self.last_capture_attempt_at = None
        logger.info(f"Screen captures {'enabled' if self.enabled else 'disabled'}")

    def on_screenshare_start(self, participant_uuid):
        self.screen_sharers.add(participant_uuid)
        # A new presentation: capture it without waiting for the interval.
        self.last_capture_attempt_at = None

    def on_screenshare_stop(self, participant_uuid):
        self.screen_sharers.discard(participant_uuid)

    def capture_if_due(self, now=None):
        if not self.enabled or not self.screen_sharers or self.is_paused_callback():
            return False
        now = time.time() if now is None else now
        if self.last_capture_attempt_at is not None and now - self.last_capture_attempt_at < self.interval_seconds:
            return False
        self.last_capture_attempt_at = now

        png = self.take_screenshot_callback()
        if not png:
            return False
        encoded = self.encode(png)
        if encoded is None:
            return False
        jpeg, width, height, thumbnail = encoded
        if self.last_thumbnail is not None and self.changed_share(thumbnail, self.last_thumbnail) < self.SAME_IMAGE_MAX_CHANGED_SHARE:
            return False
        self.last_thumbnail = thumbnail
        self.save_capture_callback(image=jpeg, width=width, height=height, timestamp_ms=int(now * 1000))
        return True

    @classmethod
    def encode(cls, png):
        """JPEG bytes, size and comparison thumbnail of a PNG screenshot."""
        image = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            logger.warning("Screen capture could not be decoded")
            return None
        height, width = image.shape[:2]
        if width > cls.MAX_WIDTH:
            height = round(height * cls.MAX_WIDTH / width)
            width = cls.MAX_WIDTH
            image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        ok, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, cls.JPEG_QUALITY])
        if not ok:
            logger.warning("Screen capture could not be encoded")
            return None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        thumbnail = cv2.resize(gray, cls.THUMBNAIL_SIZE, interpolation=cv2.INTER_AREA).astype(np.float32)
        return jpeg.tobytes(), width, height, thumbnail

    @classmethod
    def changed_share(cls, thumbnail, previous):
        return float(np.mean(np.abs(thumbnail - previous) > cls.CHANGED_PIXEL_DELTA))
