"""Worker thumbnails must not wait on Qt's native global rendering pool."""
import gc
from pathlib import Path
import tempfile
import unittest
import json
import os
import subprocess
import sys
from unittest.mock import patch
from PIL import Image
from PyQt5.QtCore import QThreadPool
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
from app.core.image_profiles import load_cached_image
from app.ui import refresh


class ThumbnailDeadlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_worker_resize_avoids_qt_scaled_and_keeps_source_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cover.png'
            Image.new('RGBA',(1200,1800),(13,57,101,128)).save(path)
            original=path.read_bytes()
            with patch.object(QImage,'scaled',side_effect=AssertionError('Qt scaling is unsafe in this worker path')):
                image=refresh.cached_refresh_image(path)
                self.assertEqual((image.width(),image.height()),(360,540))
                banner=refresh.cached_refresh_image(path,banner=True)
                self.assertEqual((banner.width(),banner.height()),(480,720))
            gc.collect()
            color=image.pixelColor(100,100)
            self.assertEqual((color.red(),color.green(),color.blue(),color.alpha()),(13,57,101,128))
            self.assertEqual(path.read_bytes(),original)

    def test_small_image_is_not_enlarged_and_bad_data_stays_a_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'small.png';Image.new('RGB',(20,30),'red').save(path)
            image=load_cached_image(path,max_size=(360,540))
            self.assertEqual((image.width(),image.height()),(20,30))
            path.write_bytes(b'not an image')
            self.assertTrue(load_cached_image(path,max_size=(360,540)).isNull())

    def test_python_thumbnail_pool_is_bounded_and_separate_from_qt_global_pool(self):
        pool=refresh.thumbnail_pool()
        self.assertIs(pool,refresh.thumbnail_pool())
        self.assertIsNot(pool,QThreadPool.globalInstance())
        self.assertEqual(pool.maxThreadCount(),2)

    def test_concurrent_images_and_scroll_complete_in_isolated_process(self):
        root=Path(__file__).resolve().parents[1]
        env=dict(os.environ,APP_PROFILE='0',QT_QPA_PLATFORM='offscreen',OFFLINE_MODE='true')
        result=subprocess.run([sys.executable,str(root/'scripts'/'audit_image_stress.py'),'--synthetic'],
                              cwd=root,env=env,capture_output=True,text=True,timeout=25,check=True)
        measured=json.loads(result.stdout)
        self.assertEqual(measured['records'],128)
        self.assertEqual(measured['synthetic_artwork'],32)
        self.assertLessEqual(measured['slots'],35)
        # Completion under a process timeout guards against a native deadlock.
        # Wall-clock smoothness remains an observed metric, not a flaky CI assertion.
        self.assertEqual([tour['tour'] for tour in measured['tours']],['cold','warm'])
