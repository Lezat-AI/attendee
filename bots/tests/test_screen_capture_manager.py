import unittest

import cv2
import numpy as np

from bots.bot_controller.screen_capture_manager import ScreenCaptureManager


def _png(color, text=""):
    image = np.full((1080, 1920, 3), color, np.uint8)
    if text:
        cv2.putText(image, text, (200, 500), cv2.FONT_HERSHEY_SIMPLEX, 6, (0, 0, 0), 12)
    return cv2.imencode(".png", image)[1].tobytes()


class ScreenCaptureManagerTest(unittest.TestCase):
    """Lezat fork: stills of shared screens, only when asked and only new ones."""

    def setUp(self):
        self.shots = []
        self.saved = []
        self.paused = False
        self.manager = ScreenCaptureManager(
            take_screenshot_callback=lambda: self.shots.pop(0) if self.shots else None,
            save_capture_callback=lambda **capture: self.saved.append(capture),
            is_paused_callback=lambda: self.paused,
        )

    def test_nothing_is_captured_until_asked_and_someone_shares(self):
        self.shots = [_png(255, "Slide 1")] * 3
        self.assertFalse(self.manager.capture_if_due(now=0))
        self.manager.set_enabled(True)
        self.assertFalse(self.manager.capture_if_due(now=1))
        self.manager.on_screenshare_start("participant-1")
        self.assertTrue(self.manager.capture_if_due(now=2))
        self.assertEqual(len(self.saved), 1)

    def test_only_new_slides_every_interval_are_kept(self):
        self.shots = [_png(255, "Slide 1"), _png(255, "Slide 1"), _png(255, "Slide 2")]
        self.manager.set_enabled(True)
        self.manager.on_screenshare_start("participant-1")

        self.assertTrue(self.manager.capture_if_due(now=0))
        self.assertFalse(self.manager.capture_if_due(now=5))  # before the interval
        self.assertFalse(self.manager.capture_if_due(now=16))  # same slide
        self.assertTrue(self.manager.capture_if_due(now=32))  # next slide

        first = self.saved[0]
        self.assertEqual((first["width"], first["height"]), (1600, 900))
        self.assertEqual(first["image"][:2], b"\xff\xd8")  # JPEG
        self.assertEqual(first["timestamp_ms"], 0)

    def test_pauses_and_stopped_shares_take_nothing(self):
        self.shots = [_png(0)] * 3
        self.manager.set_enabled(True)
        self.manager.on_screenshare_start("participant-1")
        self.paused = True
        self.assertFalse(self.manager.capture_if_due(now=0))
        self.paused = False
        self.manager.on_screenshare_stop("participant-1")
        self.assertFalse(self.manager.capture_if_due(now=20))
        self.manager.set_enabled(False)
        self.manager.on_screenshare_start("participant-1")
        self.assertFalse(self.manager.capture_if_due(now=40))
        self.assertEqual(self.saved, [])
