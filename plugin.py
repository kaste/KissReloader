from contextlib import contextmanager
from pathlib import Path
import sys

import sublime
import sublime_plugin

from typing import Iterator, List


def reload_(package_name: str, plugin_files: List[Path]):
    # Clear module cache to force reloading all modules of this package.
    plugin_names = {f"{package_name}.{file.stem}" for file in plugin_files}
    has_marker = any(map(file_has_marker, plugin_files))
    if not has_marker:
        # kiss-reloader:
        prefix = package_name + "."  # don't clear the base package
        for module_name in [
            module_name
            for module_name in sys.modules
            if module_name.startswith(prefix) and module_name not in plugin_names
        ]:
            del sys.modules[module_name]

    for file in plugin_files:
        file.touch()


def file_has_marker(file: Path) -> bool:
    try:
        content = file.read_text()
    except Exception:
        return False
    else:
        # The marker indicates by convention that just touching
        # the file reloads the package.  That typically means,
        # it has the reloader implemented and just need our command
        # to trigger it.
        return "# kiss-reloader" in content


class kiss_reloader_reload(sublime_plugin.ApplicationCommand):
    def run(self, package_name: str) -> None:
        pp = Path(sublime.packages_path())
        package_directory = pp / package_name
        if not package_directory.exists():
            print(f"Can't find installation for {package_name!r}.  {package_directory} does not exist.")
            return

        python_files = sorted(
            path
            for path in package_directory.glob("*.py")
            if path.name != "__init__.py"
        )
        s = "s" if len(python_files) > 1 else ""
        print("package_directory:", package_directory)
        print(f"plugin_file{s}:", ", ".join(f.name for f in python_files))
        with report_reload_status(package_name):
            reload_(package_name, python_files)


@contextmanager
def report_reload_status(package_name: str) -> Iterator[None]:
    capture = ConsoleCapture().start()
    try:
        yield
    finally:
        sublime.set_timeout(
            lambda: _show_reload_status(package_name, capture),
            1000
        )


def _show_reload_status(package_name: str, capture: "ConsoleCapture") -> None:
    output = capture.stop()
    aw = sublime.active_window()
    if "Traceback (most recent call last):" in output:
        aw.status_message(f"{package_name} 💣ed. 😒.")
    else:
        aw.status_message(f"{package_name} has 🙌 reloaded.")


class kiss_reloader_reload_current_package(sublime_plugin.WindowCommand):
    def run(self) -> None:
        window = self.window
        candidates = list(filter(None, [
            view.file_name() if (view := window.active_view()) else None,
            folders[0] if (folders := window.folders()) else None
        ]))
        if not candidates:
            print(
                "Abort. There is neither a view with a file name "
                "nor a folder in the sidebar open.")
            return

        pp = Path(sublime.packages_path())
        for candidate in candidates:
            try:
                package_name = Path(candidate).relative_to(pp).parts[0]
            except LookupError:
                ...
            else:
                print("reload:", package_name)
                sublime.run_command("kiss_reloader_reload", {"package_name": package_name})
                return


ACTIVE_CAPTURE = None


class ConsoleCapture:
    def __init__(self):
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.chunks = []
        self.stdout_tee = TeeStream(self.stdout, self.chunks)
        self.stderr_tee = TeeStream(self.stderr, self.chunks)

    def start(self) -> "ConsoleCapture":
        global ACTIVE_CAPTURE
        if ACTIVE_CAPTURE:
            ACTIVE_CAPTURE.stop()

        sys.stdout = self.stdout_tee
        sys.stderr = self.stderr_tee
        ACTIVE_CAPTURE = self
        return self

    def stop(self) -> str:
        global ACTIVE_CAPTURE
        if sys.stdout is self.stdout_tee:
            sys.stdout = self.stdout
        if sys.stderr is self.stderr_tee:
            sys.stderr = self.stderr
        if ACTIVE_CAPTURE is self:
            ACTIVE_CAPTURE = None
        return "".join(self.chunks)


class TeeStream:
    def __init__(self, stream, chunks) -> None:
        self.stream = stream
        self.chunks = chunks

    def write(self, text):
        self.chunks.append(str(text))
        return self.stream.write(text)

    def flush(self) -> None:
        return self.stream.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)
