"""Repair ICC metadata without recompressing or hiding Qt diagnostics."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from PyQt5.QtCore import qInstallMessageHandler
from PyQt5.QtGui import QImage
from app.core.image_profiles import repair_jpeg_profile,load_cached_image


class ImageProfileTests(unittest.TestCase):
    def jpeg(self,tag_size=11,split=False,profile_class=None):
        image=Image.new('RGB',(16,24),(24,86,137));stream=io.BytesIO();image.save(stream,format='JPEG');raw=stream.getvalue()
        profile=bytearray(160);profile[:4]=(160).to_bytes(4,'big');profile[36:40]=b'acsp';profile[128:132]=(1).to_bytes(4,'big')
        if profile_class:profile[12:16]=profile_class
        profile[132:136]=b'cprt';profile[136:140]=(144).to_bytes(4,'big');profile[140:144]=tag_size.to_bytes(4,'big')
        profile[144:155]=b'text'+bytes(4)+b'abc'
        chunks=[bytes(profile[:100]),bytes(profile[100:])] if split else [bytes(profile)]
        segments=b''
        for n,chunk in enumerate(chunks,1):
            content=b'ICC_PROFILE\0'+bytes((n,len(chunks)))+chunk
            segments+=b'\xff\xe2'+(len(content)+2).to_bytes(2,'big')+content
        return raw[:2]+segments+raw[2:]

    def test_short_copyright_tag_is_repaired_without_changing_pixels_or_scan(self):
        original=self.jpeg();fixed=repair_jpeg_profile(original)
        self.assertNotEqual(fixed,original);self.assertEqual(len(fixed),len(original))
        self.assertEqual(original[original.index(b'\xff\xda'):],fixed[fixed.index(b'\xff\xda'):])
        with Image.open(io.BytesIO(original)) as before,Image.open(io.BytesIO(fixed)) as after:
            self.assertEqual(before.tobytes(),after.tobytes())
        self.assertEqual(repair_jpeg_profile(fixed),fixed)

    def test_valid_unrecognised_truncated_and_split_profiles(self):
        valid=self.jpeg(12);self.assertEqual(repair_jpeg_profile(valid),valid)
        for raw in (b'',b'not an image',self.jpeg()[:50],b'\xff\xd8\xff\xe2\x00\x01'):
            self.assertEqual(repair_jpeg_profile(raw),raw)
        self.assertNotEqual(repair_jpeg_profile(self.jpeg(split=True)),self.jpeg(split=True))

    def test_worker_repairs_cache_atomically_and_retains_qt_warnings(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cover.jpg';path.write_bytes(self.jpeg());messages=[]
            previous=qInstallMessageHandler(lambda kind,context,message:messages.append(message))
            try:
                image=load_cached_image(path);again=QImage(str(path))
                self.assertFalse(image.isNull());self.assertFalse(again.isNull())
                self.assertFalse(any('failed minimal tag size sanity' in message for message in messages))
            finally:qInstallMessageHandler(previous)
            self.assertEqual(list(Path(folder).glob('*.profile')),[])

    def test_download_repairs_before_validation_and_cache_write(self):
        from app.core import anilist_client as client
        with tempfile.TemporaryDirectory() as folder,patch.object(client,'COVERS_DIR',Path(folder)),patch.object(client.requests,'get') as get:
            get.return_value.content=self.jpeg()
            self.assertEqual(client._download_artwork('https://example.test/cover.jpg','test.jpg'),'test.jpg')
            self.assertEqual((Path(folder)/'test.jpg').read_bytes(),repair_jpeg_profile(self.jpeg()))

    def test_printer_profile_is_removed_losslessly_including_split_segments(self):
        for split in (False,True):
            original=self.jpeg(12,split=split,profile_class=b'prtr')
            # Preserve an unrelated APP2 segment alongside the ICC segments.
            other=b'\xff\xe2'+(2+len(b'OTHER_APP')).to_bytes(2,'big')+b'OTHER_APP'
            original=original[:2]+other+original[2:]
            cleaned=repair_jpeg_profile(original)
            self.assertNotIn(b'ICC_PROFILE\0',cleaned);self.assertIn(other,cleaned)
            self.assertEqual(original[original.index(b'\xff\xda'):],cleaned[cleaned.index(b'\xff\xda'):])
            with Image.open(io.BytesIO(original)) as before,Image.open(io.BytesIO(cleaned)) as after:
                self.assertEqual(before.tobytes(),after.tobytes());self.assertFalse(after.info.get('icc_profile'))
            self.assertEqual(repair_jpeg_profile(cleaned),cleaned)
            messages=[];previous=qInstallMessageHandler(lambda kind,context,message:messages.append(message))
            try:self.assertFalse(QImage.fromData(cleaned).isNull())
            finally:qInstallMessageHandler(previous)
            self.assertFalse(any('Unsupported ICC profile class' in message for message in messages))

    def test_non_printer_profiles_are_kept(self):
        for kind in (b'mntr',b'scnr',b'link',b'xxxx'):
            original=self.jpeg(12,profile_class=kind)
            self.assertEqual(repair_jpeg_profile(original),original)
