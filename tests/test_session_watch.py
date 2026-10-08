import importlib.util
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'helper'))
import session_watch as watch
import bridge


class SessionSafetyTests(unittest.TestCase):
    def test_minimized_and_hidden_windows_are_preserved(self):
        state = watch.WindowLifetime()
        self.assertFalse(state.closed(({1}, {1}), 0))
        self.assertFalse(state.closed(({1}, set()), 600))
        self.assertFalse(state.closed(({1}, set()), 10000))

    def test_window_recreation_resets_close_grace(self):
        state = watch.WindowLifetime()
        state.closed(({1}, {1}), 0)
        self.assertFalse(state.closed((set(), set()), 5))
        self.assertFalse(state.closed(({2}, {2}), 70))
        self.assertFalse(state.closed((set(), set()), 100))
        self.assertTrue(state.closed((set(), set()), 160))

    def test_hidden_replacement_window_is_preserved(self):
        state = watch.WindowLifetime()
        state.closed(({1, 9}, {1}), 0)
        self.assertFalse(state.closed(({2, 9}, set()), 5))
        self.assertFalse(state.closed(({2, 9}, set()), 1000))
        self.assertFalse(state.closed(({9}, set()), 1005))
        self.assertTrue(state.closed(({9}, set()), 1065))

    def test_inconclusive_observation_never_kills(self):
        state = watch.WindowLifetime()
        self.assertFalse(state.closed((set(), set()), 1000))
        state.closed(({1}, {1}), 1001)
        state.closed((set(), set()), 1010)
        self.assertFalse(state.closed(None, 1080))
        self.assertFalse(state.closed((set(), set()), 1081))

    def test_pid_reuse_or_different_copy_never_terminated(self):
        identity = ('old', 'game', 'dungeons-win64-shipping.exe')
        with patch.object(watch, 'rows', return_value={1: ('new', 'game', identity[2])}), patch.object(watch.os, 'kill') as kill:
            self.assertFalse(watch.terminate_game(1, identity, Path('/a'), None, None)); kill.assert_not_called()
        with patch.object(watch, 'rows', return_value={1: identity}), patch.object(watch, 'files', return_value=[Path('/other')]), patch.object(watch.os, 'kill') as kill:
            self.assertFalse(watch.terminate_game(1, identity, Path('/a'), None, None)); kill.assert_not_called()

    def test_preserves_preexisting_steam_and_other_apps(self):
        with patch.object(watch, 'event'), patch.object(watch, 'rows', return_value={}), patch.object(watch, 'bottle_rows') as query, patch.object(watch.subprocess, 'Popen') as launch:
            watch.cleanup(Path('/bottle'), Path('/game'), False)
            query.assert_not_called(); launch.assert_not_called()
        for result in (None, {1: ('time', 'editor.exe', 'editor.exe')}, {2: ('time', 'other-game.exe', 'other-game.exe')}):
            with patch.object(watch, 'event'), patch.object(watch, 'rows', return_value={}), patch.object(watch, 'bottle_rows', return_value=result), patch.object(watch.subprocess, 'Popen') as launch:
                watch.cleanup(Path('/bottle'), Path('/game'), True); launch.assert_not_called()

    def test_active_download_preserves_steam(self):
        with patch.object(watch, 'event'), patch.object(watch, 'rows', return_value={}), patch.object(watch, 'bottle_rows', return_value={1: ('time', 'steam.exe', 'steam.exe')}), patch.object(watch, 'downloads_pending', return_value=True), patch.object(watch.subprocess, 'Popen') as launch:
            watch.cleanup(Path('/bottle'), Path('/game'), True); launch.assert_not_called()

    def test_cleanup_only_shuts_selected_empty_prefix(self):
        with patch.object(watch, 'event'), patch.object(watch, 'rows', return_value={}), patch.object(watch, 'bottle_rows', side_effect=[{1: ('time','steam.exe','steam.exe')}, {}]), patch.object(watch, 'downloads_pending', return_value=False), patch.object(watch.time, 'sleep'), patch.object(watch.subprocess, 'Popen') as launch, patch.object(watch.subprocess, 'run') as stop:
            watch.cleanup(Path('/bottles/Selected'), Path('/game'), True)
            self.assertIn('Selected', launch.call_args.args[0])
            self.assertEqual(stop.call_args.kwargs['env']['WINEPREFIX'], '/bottles/Selected')
            self.assertEqual(stop.call_args.args[0][-1], '-k')

    def test_download_guard_checks_external_libraries(self):
        with tempfile.TemporaryDirectory() as t:
            b=Path(t); a=b/'drive_c/Program Files (x86)/Steam/steamapps'; a.mkdir(parents=True)
            external=b/'drive_c/Other/steamapps';external.mkdir(parents=True)
            (a/'libraryfolders.vdf').write_text('"path" "C:\\\\Other"')
            (a/'appmanifest_1.acf').write_text('"StateFlags" "4"')
            (external/'appmanifest_2.acf').write_text('"StateFlags" "1048576"')
            self.assertTrue(watch.downloads_pending(b,a/'common/Game'))
            (external/'appmanifest_2.acf').write_text('"StateFlags" "4" "BytesToDownload" "3" "BytesDownloaded" "3"')
            self.assertFalse(watch.downloads_pending(b,a/'common/Game'))

    def test_auth_wait_sleeps_and_wakes_for_new_request(self):
        with tempfile.TemporaryDirectory() as t:
            wake=bridge.DirectoryWakeup(t)
            try:
                start=time.monotonic();wake.wait(.12)
                self.assertGreaterEqual(time.monotonic()-start,.10)
                thread=threading.Thread(target=lambda:(time.sleep(.1),(Path(t)/'request.req').write_bytes(b'test')))
                thread.start();start=time.monotonic();wake.wait(3);thread.join()
                self.assertLess(time.monotonic()-start,1)
            finally:wake.close()


if __name__=='__main__':unittest.main()
