import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import test_ui_regressions as support
from PyQt5.QtCore import Qt
from app.ui.pages.merge_page import MergePage, MergeWorker, selected_plan
from app.core.consolidation import make_plan


class MergePageTests(unittest.TestCase):
    setUp = support.Regressions.setUp
    tearDown = support.Regressions.tearDown

    @classmethod
    def setUpClass(cls):
        support.Regressions.setUpClass.__func__(cls)

    def sample_plan(self):
        root = Path(self.temp.name) / 'source'
        for title in ('Alpha', 'Beta'):
            folder = root / title / 'Season 1'
            folder.mkdir(parents=True)
            (folder / f'{title} S01E01.mkv').write_bytes(title.encode())
        return make_plan([root], Path(self.temp.name) / 'destination')

    def test_selection_is_explicit_and_subset_contains_only_chosen_anime(self):
        plan = self.sample_plan()
        page = MergePage()
        page.plan_ready({'plan': plan, 'report': 'test preview'})
        self.assertEqual(page.selected_titles(), set())
        self.assertFalse(page.move_button.isEnabled())
        page.table.item(0, 0).setCheckState(Qt.Checked)
        self.assertFalse(page.move_button.isEnabled())
        page.confirm.setChecked(True)
        self.assertTrue(page.move_button.isEnabled())
        subset = selected_plan(plan, page.selected_titles())
        self.assertEqual({m['series'] for m in subset['moves']}, {'Alpha'})
        page.destination.setText('Different destination')
        self.assertIsNone(page.plan)
        self.assertFalse(page.move_button.isEnabled())
        page.deleteLater()

    def test_worker_moves_one_anime_and_leaves_other_untouched(self):
        plan = self.sample_plan()
        alpha_plan = selected_plan(plan, {'Alpha'})
        worker = MergeWorker(alpha_plan)
        results, errors = [], []
        worker.completed.connect(results.append)
        worker.failed.connect(errors.append)
        worker.run()
        self.assertEqual(errors, [])
        self.assertEqual(len(results[0]['moved']), 1)
        beta = next(m for m in plan['moves'] if m['series'] == 'Beta')
        self.assertTrue(Path(beta['source']).exists())
        self.assertFalse(Path(beta['target']).exists())
        report = Path(results[0]['report'])
        self.assertTrue((report / 'before-moves.db').exists())
        self.assertTrue((report / 'move-journal.jsonl').exists())

    def test_stop_after_first_file_preserves_remaining_sources(self):
        from app.core.consolidation import apply_plan
        plan = self.sample_plan()
        progressed = []
        result = apply_plan(plan, Path(self.temp.name) / 'journal.jsonl',
                            progress=lambda *args: progressed.append(args), should_stop=lambda: bool(progressed))
        self.assertEqual(len(result['moved']), 1)
        self.assertTrue(result['cancelled'])
        self.assertEqual(sum(Path(m['source']).exists() for m in plan['moves']), 1)

    def test_merge_worker_is_in_close_protection(self):
        from types import SimpleNamespace
        from app.ui.main_window import MainWindow
        worker = Mock()
        worker.isRunning.return_value = True
        merge = SimpleNamespace(_merge_worker=worker)
        organizer = SimpleNamespace(merge_page=merge)
        host = SimpleNamespace(organizer_page=organizer, _navigation_pages=[])
        self.assertIs(MainWindow._active_task_page(host, protect_only=True), merge)

    def test_review_only_anime_is_selectable_and_can_approve_unknown_arc(self):
        plan = self.sample_plan()
        entry = next(m for m in plan['moves'] if m['series'] == 'Alpha')
        entry['review_reason'] = 'Absolute episode numbering; arc needs review'
        page = MergePage()
        page.plan_ready({'plan': plan, 'report': 'test preview'})
        page.table.selectRow(0)
        page.table.item(0, 0).setCheckState(Qt.Checked)
        self.assertEqual(page.selected_titles(), {'Alpha'})
        page.confirm.setChecked(True)
        self.assertFalse(page.move_button.isEnabled())
        self.assertTrue(page.approve_button.isEnabled())
        page.approve_folder()
        updated = next(m for m in page.plan['moves'] if m['series'] == 'Alpha')
        self.assertIsNone(updated['review_reason'])
        self.assertEqual(updated['release'], 'Unassigned episodes')
        self.assertIn('Unassigned episodes', updated['target'])
        self.assertFalse(page.confirm.isChecked())
        page.confirm.setChecked(True)
        self.assertTrue(page.move_button.isEnabled())
        self.assertTrue(Path(updated['source']).exists())
        page.deleteLater()

    def test_approval_rejects_parent_paths_and_leaves_preview_unchanged(self):
        from app.core.consolidation import approve_release_group
        plan = self.sample_plan()
        plan['moves'][0]['review_reason'] = 'Needs arc'
        original = plan['moves'][0]['target']
        with self.assertRaises(ValueError):
            approve_release_group(plan, plan['moves'][0]['series'], '../outside')
        self.assertEqual(plan['moves'][0]['target'], original)
        self.assertEqual(plan['moves'][0]['review_reason'], 'Needs arc')
