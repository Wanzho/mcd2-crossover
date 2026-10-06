import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import game_process as g


class GameProcessTests(unittest.TestCase):
    """Every ps/lsof call is a synthetic fixture; Wine is never invoked."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.bottle = self.root / 'Bottles/Steam'
        self.other = self.root / 'Bottles/Other'
        self.selected = self.make_game(self.bottle, 'Minecraft Dungeons II')
        self.d1 = self.make_game(self.bottle, 'MinecraftDungeons')
        self.other_d2 = self.make_game(self.other, 'Minecraft Dungeons II')

    def tearDown(self):
        self.temp.cleanup()

    def make_game(self, bottle, folder):
        file = bottle / 'drive_c/Program Files (x86)/Steam/steamapps/common' / folder / 'Dungeons/Binaries/Win64/Dungeons-Win64-Shipping.exe'
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'not executable: fixture only')
        return file

    def windows(self, file, bottle=None):
        bottle = bottle or self.bottle
        return 'C:\\' + str(file.relative_to(bottle / 'drive_c')).replace('/', '\\')

    def query(self, rows='', files=None, ps_status=0, lsof_status=0):
        files = files or {}
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            self.assertEqual(kwargs['timeout'], 3 if args[0] == '/bin/ps' else 2)
            if args == ['/bin/ps', '-axo', 'pid=,comm=']:
                return subprocess.CompletedProcess(args, ps_status, stdout=rows)
            self.assertEqual(args[:3], ['/usr/sbin/lsof', '-a', '-p'])
            self.assertEqual(args[-1], '-Fpn')
            pid = int(args[3])
            value = files.get(pid, '')
            if isinstance(value, Exception):
                raise value
            if isinstance(value, list):
                value = 'p' + str(pid) + '\n' + ''.join('n' + str(p) + '\n' for p in value)
            return subprocess.CompletedProcess(args, lsof_status, stdout=value)
        return run, calls

    def report(self, rows='', files=None, **options):
        run, calls = self.query(rows, files, **options)
        return g.inspect_processes(self.selected, self.bottle, shared_steam=True, run=run), calls

    def test_selected_game_requires_physical_file_evidence(self):
        run, _ = self.query('101 ' + self.windows(self.selected) + '\n', {101: [self.selected]})
        for override in (False, True):
            with self.subTest(override=override), self.assertRaises(g.RunningGameError) as failure:
                g.require_idle(self.selected, self.bottle, shared_steam=True, ignore_other=override, run=run)
            self.assertEqual((failure.exception.marker, failure.exception.exit_code), (g.SELECTED, 20))

    def test_d1_in_shared_bottle_has_different_result_and_explicit_override(self):
        run, _ = self.query('102 ' + self.windows(self.d1) + '\n', {102: [self.d1]})
        with self.assertRaises(g.RunningGameError) as failure:
            g.require_idle(self.selected, self.bottle, shared_steam=True, run=run)
        self.assertEqual((failure.exception.marker, failure.exception.exit_code), (g.SHARED, 21))
        report = g.require_idle(self.selected, self.bottle, shared_steam=True, ignore_other=True, run=run)
        self.assertEqual(report.selected_pids, ())
        self.assertEqual(report.shared_pids, (102,))

    def test_two_bottles_with_identical_windows_paths_are_distinguished(self):
        self.assertEqual(self.windows(self.selected), self.windows(self.other_d2, self.other))
        report, calls = self.report('103 ' + self.windows(self.other_d2, self.other) + '\n', {103: [self.other_d2]})
        self.assertEqual(report, g.ProcessReport())
        self.assertEqual(len(calls), 2)

    def test_d1_in_another_bottle_does_not_block(self):
        other_d1 = self.make_game(self.other, 'MinecraftDungeons')
        report, _ = self.report('104 ' + self.windows(other_d1, self.other), {104: [other_d1]})
        self.assertEqual(report, g.ProcessReport())

    def test_other_steam_game_in_shared_bottle_warns_before_restart(self):
        game = self.bottle / 'drive_c/Program Files (x86)/Steam/steamapps/common/OtherGame/OtherGame.exe'
        game.parent.mkdir(parents=True); game.write_bytes(b'fixture')
        report, _ = self.report('105 ' + self.windows(game), {105: [game]})
        self.assertEqual(report.shared_pids, (105,))

    def test_launcher_setup_does_not_consider_shared_steam(self):
        run, _ = self.query('106 ' + self.windows(self.d1), {106: [self.d1]})
        self.assertEqual(g.require_idle(self.selected, self.bottle, run=run), g.ProcessReport())

    def test_selected_game_wins_over_other_or_uncertain_processes(self):
        run, _ = self.query('107 ' + self.windows(self.d1) + '\n108 ' + self.windows(self.selected),
                            {107: '', 108: [self.selected]})
        with self.assertRaises(g.RunningGameError) as failure:
            g.require_idle(self.selected, self.bottle, shared_steam=True, ignore_other=True, run=run)
        self.assertEqual(failure.exception.exit_code, 20)

    def test_missing_pid_evidence_is_ambiguous_not_confirmed(self):
        run, _ = self.query('109 ' + self.windows(self.selected), {109: 'n' + str(self.selected) + '\n'})
        with self.assertRaises(g.RunningGameError) as failure:
            g.require_idle(self.selected, self.bottle, run=run)
        self.assertEqual((failure.exception.marker, failure.exception.exit_code), (g.AMBIGUOUS, 22))
        self.assertTrue(g.require_idle(self.selected, self.bottle, ignore_other=True, run=run).ambiguous)

    def test_wrong_or_mixed_lsof_pid_is_ambiguous(self):
        for files in ('p999\nn' + str(self.selected), 'p110\nn' + str(self.selected) + '\np999\n'):
            with self.subTest(files=files):
                report, _ = self.report('110 ' + self.windows(self.selected), {110: files})
                self.assertTrue(report.ambiguous)
                self.assertEqual(report.selected_pids, ())

    def test_unavailable_queries_do_not_mean_idle(self):
        report, _ = self.report(ps_status=1)
        self.assertTrue(report.ambiguous)
        for status, error in ((1, None), (0, subprocess.TimeoutExpired('lsof', 2)), (0, FileNotFoundError())):
            with self.subTest(status=status, error=error):
                report, _ = self.report('111 ' + self.windows(self.selected), {111: error or [self.selected]}, lsof_status=status)
                self.assertTrue(report.ambiguous)
                self.assertEqual(report.selected_pids, ())

    def test_no_candidate_does_not_query_unrelated_open_files(self):
        report, calls = self.report('0 kernel_task\n1 /sbin/launchd\n112 C:\\Program Files (x86)\\Steam\\steam.exe\n')
        self.assertEqual(report, g.ProcessReport())
        self.assertEqual(len(calls), 1)

    def test_name_case_and_windows_slashes_do_not_change_physical_identity(self):
        report, _ = self.report('113 ' + self.windows(self.selected).swapcase().replace('\\', '/'), {113: [self.selected]})
        self.assertEqual(report.selected_pids, (113,))

    def test_symlink_file_identity_is_confirmed(self):
        link = self.root / 'ExternalLibrary/Dungeons-Win64-Shipping.exe'
        link.parent.mkdir(); link.symlink_to(self.selected)
        report, _ = self.report('114 Z:\\ExternalLibrary\\Dungeons-Win64-Shipping.exe', {114: [link]})
        self.assertEqual(report.selected_pids, (114,))

    def test_bootstrapper_for_selected_copy_is_protected(self):
        bootstrapper = self.selected.parents[3] / 'Dungeons.exe'
        bootstrapper.write_bytes(b'fixture bootstrapper')
        report, _ = self.report('115 ' + self.windows(bootstrapper), {115: [bootstrapper]})
        self.assertEqual(report.selected_pids, (115,))

    def test_prefix_collision_bottle_is_not_selected_bottle(self):
        colliding = self.root / 'Bottles/SteamExtra'
        other = self.make_game(colliding, 'Minecraft Dungeons II')
        report, _ = self.report('116 ' + self.windows(other, colliding), {116: [other]})
        self.assertEqual(report, g.ProcessReport())

    def test_external_library_without_bottle_evidence_remains_ambiguous(self):
        external = self.root / 'ExternalLibrary/Dungeons-Win64-Shipping.exe'
        external.parent.mkdir(); external.write_bytes(b'other fixture')
        report, _ = self.report('117 Z:\\ExternalLibrary\\Dungeons-Win64-Shipping.exe', {117: [external]})
        self.assertTrue(report.ambiguous)
        self.assertEqual(report.selected_pids, ())

    def test_malformed_process_listing_is_explicitly_uncertain(self):
        for rows in ('Dungeons-Win64-Shipping.exe', '-1 Dungeons-Win64-Shipping.exe',
                     '118 Dungeons-Win64-Shipping.exe\n118 Dungeons-Win64-Shipping.exe',
                     '0 Dungeons-Win64-Shipping.exe', '999999999999 Dungeons-Win64-Shipping.exe'):
            with self.subTest(rows=rows):
                report, _ = self.report(rows)
                self.assertTrue(report.ambiguous)

    def test_unrelated_string_containing_dungeons_is_not_a_game_candidate(self):
        report, calls = self.report('119 /Applications/NotDungeonsShipping.app/Contents/MacOS/editor\n')
        self.assertEqual(report, g.ProcessReport())
        self.assertEqual(len(calls), 1)

    def test_inherited_bottle_working_directory_is_not_bottle_identity(self):
        report, _ = self.report('120 ' + self.windows(self.other_d2, self.other),
                                {120: [self.selected.parent, self.bottle, self.other_d2]})
        self.assertEqual(report, g.ProcessReport())
        report, _ = self.report('120 ' + self.windows(self.selected), {120: [self.bottle]})
        self.assertTrue(report.ambiguous)
        self.assertEqual(report.shared_pids, ())

    def test_bottles_parent_directory_does_not_identify_another_bottle(self):
        report, _ = self.report('121 ' + self.windows(self.selected), {121: [self.bottle.parent]})
        self.assertTrue(report.ambiguous)

    def test_deleted_mapped_selected_path_remains_protected(self):
        run, _ = self.query('122 ' + self.windows(self.selected),
                            {122: 'p122\nn'+str(self.selected)+' (deleted)\n'})
        self.assertEqual(g.inspect_processes(self.selected,self.bottle,run=run).selected_pids,(122,))

    def test_query_output_bounds_fail_closed(self):
        for rows in ('x'*(g.MAX_QUERY_BYTES+1), '\n'.join(str(200+i)+' Dungeons-Win64-Shipping.exe' for i in range(g.MAX_CANDIDATES+1))):
            with self.subTest(length=len(rows)):
                report, _ = self.report(rows)
                self.assertTrue(report.ambiguous)
        report, _ = self.report('123 '+self.windows(self.selected),{123:'p123\n'+'x'*(g.MAX_QUERY_BYTES+1)})
        self.assertTrue(report.ambiguous)


if __name__ == '__main__':
    unittest.main()
