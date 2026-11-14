"""Tests for PotPlayer playback tracking and session integration."""
import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from app import db
from app.core import playback, potplayer, download_queue
from app.ui.components import transfer_row
from app.ui.home_style import colors


class PotPlayerPlaybackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(os.environ.get("TEMP", ".")) / "animevault_pot_test"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.video = self.tmp / "[Sub] Attack on Titan - 01.mkv"
        self.video.write_bytes(b"dummy video data")

    def tearDown(self):
        try:
            if self.video.is_file():
                self.video.unlink()
            if self.tmp.is_dir():
                self.tmp.rmdir()
        except Exception:
            pass

    def test_potplayer_session_arguments(self):
        # Session without prior progress
        session = playback.launch_session("potplayer", self.video, resume=False)
        self.assertIsNotNone(session)
        self.assertIn("/new", session.arguments)
        self.assertFalse(any(a.startswith("/seek=") for a in session.arguments))

        # Session with resume argument
        with patch.object(playback, "saved_progress", return_value={"position": 450.5, "duration": 1200.0}):
            session_resume = playback.launch_session("potplayer", self.video, resume=True)
            self.assertIn("/new", session_resume.arguments)
            seek_arg = next((a for a in session_resume.arguments if a.startswith("/seek=")), None)
            self.assertIsNotNone(seek_arg)
            self.assertIn("450.5", seek_arg)

    def test_potplayer_window_detection(self):
        fake_process = Mock()
        fake_process.pid = 9999

        # Case 1: Window matches filename in title
        with patch("win32process.GetWindowThreadProcessId", return_value=(1, 9999)), \
             patch("win32gui.GetClassName", return_value="PotPlayer64"), \
             patch("win32gui.GetWindowText", return_value="[Sub] Attack on Titan - 01.mkv - PotPlayer"), \
             patch("win32gui.EnumWindows", side_effect=lambda cb, _: cb(12345, None)):
            hwnd = potplayer.window_for(fake_process, self.video)
            self.assertEqual(hwnd, 12345)

        # Case 2: Window has startup generic title -> should return hwnd or raise TimeoutError
        with patch("win32process.GetWindowThreadProcessId", return_value=(1, 9999)), \
             patch("win32gui.GetClassName", return_value="PotPlayer64"), \
             patch("win32gui.GetWindowText", return_value="PotPlayer"), \
             patch("win32gui.EnumWindows", side_effect=lambda cb, _: cb(12345, None)):
            hwnd = potplayer.window_for(fake_process, self.video)
            self.assertEqual(hwnd, 12345)

        # Case 3: Window has completely different media -> MediaChanged
        with patch("win32process.GetWindowThreadProcessId", return_value=(1, 9999)), \
             patch("win32gui.GetClassName", return_value="PotPlayer64"), \
             patch("win32gui.GetWindowText", return_value="Naruto Shippuden 01.mkv - PotPlayer"), \
             patch("win32gui.EnumWindows", side_effect=lambda cb, _: cb(12345, None)):
            with self.assertRaises(playback.MediaChanged):
                potplayer.window_for(fake_process, self.video)

    def test_potplayer_poll_and_progress_saving(self):
        fake_process = Mock()
        fake_process.pid = 9999
        fake_process.poll.return_value = None

        with patch("app.core.potplayer.window_for", return_value=12345), \
             patch("app.core.potplayer.send") as mock_send, \
             patch("app.core.playback.episode_ids", return_value=[42]), \
             patch("app.core.playback.save_progress") as mock_save:

            # Send queries: 20482=duration ms (1200000 -> 1200s), 20484=pos ms (300000 -> 300s), 20486=status (2=playing)
            def fake_send(hwnd, msg, query, val=0):
                if query == 20482:
                    return 1200000
                elif query == 20484:
                    return 300000
                elif query == 20486:
                    return 2
                return 0

            mock_send.side_effect = fake_send

            session = playback.Session("potplayer", self.video, resume=False)
            session.process = fake_process
            session.last_save = 0  # Force save

            state = session.poll()
            self.assertEqual(state["position"], 300.0)
            self.assertEqual(state["duration"], 1200.0)
            self.assertFalse(state["paused"])
            self.assertTrue(state["active"])
            mock_save.assert_called_with([42], 300.0, 1200.0)

    def test_potplayer_toggle(self):
        fake_process = Mock()
        fake_process.pid = 9999
        fake_process.poll.return_value = None

        with patch("app.core.potplayer.window_for", return_value=12345), \
             patch("app.core.potplayer.send") as mock_send:
            session = playback.Session("potplayer", self.video, resume=False)
            session.process = fake_process
            session.toggle()
            mock_send.assert_called_with(12345, 273, 10014)

    def test_download_queue_completed_and_seeding_progress_and_colors(self):
        # Completed job with partial progress in DB
        completed_item = {
            "id": 1,
            "status": "complete",
            "indexed": True,
            "progress": 0.53,
            "downloaded": 340 * 1024 * 1024,
            "total": 645 * 1024 * 1024,
        }
        self.assertEqual(download_queue.status(completed_item), "Completed")
        prog, done, total = download_queue.progress_values(completed_item)
        self.assertEqual(prog, 1.0)
        self.assertEqual(done, 645 * 1024 * 1024)
        self.assertEqual(total, 645 * 1024 * 1024)

        # Seeding job
        seeding_item = {
            "id": 2,
            "status": "seeding",
            "progress": 0.8,
            "downloaded": 400 * 1024 * 1024,
            "total": 500 * 1024 * 1024,
            "upload_rate": 250000,
        }
        self.assertEqual(download_queue.status(seeding_item), "Seeding")
        prog, done, total = download_queue.progress_values(seeding_item)
        self.assertEqual(prog, 1.0)
        self.assertEqual(done, 500 * 1024 * 1024)

        # Color palette check
        c = colors()
        self.assertIn("blue", c)
        self.assertIn("orange", c)
        self.assertIn("coral", c)


if __name__ == "__main__":
    unittest.main()
