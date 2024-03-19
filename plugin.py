from pathlib import Path
import sys

import sublime
import sublime_plugin

from typing import List


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

        python_files = sorted([path for path in package_directory.glob("*.py")])
        s = "s" if len(python_files) > 1 else ""
        print("package_directory:", package_directory)
        print(f"plugin_file{s}:", ", ".join(f.name for f in python_files))
        reload_(package_name, python_files)


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
