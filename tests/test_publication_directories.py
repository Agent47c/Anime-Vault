import contextlib,io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import check_publication


class PublicationDirectoryTests(unittest.TestCase):
    def check(self,published):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'reference').mkdir()
            (root/'reference'/'design.html').write_text('Example',encoding='utf-8')
            (root/'README.md').write_text('[Reference](reference/)',encoding='utf-8')
            names=['README.md']+(['reference/design.html'] if published else [])
            output=io.StringIO()
            with patch.object(check_publication,'ROOT',root),patch('sys.argv',['check_publication.py']),patch.object(check_publication.subprocess,'check_output',return_value=('\0'.join(names)+'\0').encode()),contextlib.redirect_stdout(output):
                result=check_publication.main()
            return result,output.getvalue()

    def test_local_only_directory_is_rejected(self):
        result,output=self.check(False)
        self.assertEqual(result,1);self.assertIn('linked directory not in public snapshot',output)

    def test_published_reference_directory_is_accepted(self):
        result,output=self.check(True)
        self.assertEqual(result,0);self.assertNotIn('ERROR',output)
