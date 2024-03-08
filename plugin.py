from pathlib import Path
import sys

import sublime
import sublime_plugin


def reload_(package_name: str, plugin_file: Path):
    # Clear module cache to force reloading all modules of this package.
    prefix = package_name + "."  # don't clear the base package
    for module_name in [
        module_name
        for module_name in sys.modules
        if module_name.startswith(prefix) and module_name != __name__
    ]:
        del sys.modules[module_name]

    plugin_file.touch()


class kiss_reloader_reload(sublime_plugin.ApplicationCommand):
    def run(self, package_name: str) -> None:
        pp = Path(sublime.packages_path())
        package_directory = pp / package_name
        if not package_directory.exists():
            print(f"Can't find installation for {package_name!r}.  {package_directory} does not exist.")
            return

        python_files = [path for path in package_directory.glob("*.py") if path.name != "__init__.py"]
        if len(python_files) > 1:
            print(f"Skip reloading. {package_name!r} has more than one entrypoint in its root directory.")
            return

        print("package_directory:", package_directory)
        print("plugin_file:", python_files[0])
        reload_(package_name, python_files[0])


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
