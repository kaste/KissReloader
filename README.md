# KissReloader

The plugin packages a new simplified reloader.

Choose `kiss-reload: Reload Current Package` from the Command Palette to reload
the plugin you're currently looking at.

There is also an `ApplicationCommand` to reload a specific package at will, e.g.:

```json5
    {
        "command": "kiss_reloader_reload",
        "args": {"package_name": "GitSavvy"}
    },
```

# Add a reloader to your package

You may want to add reloader code to your main/root plugin so it actually reloads
automatically if Package Control pushes an update.

`KissReloader` watches out for the conventional `# kiss-reloader` comment and
prevents a double reload.

Note: `__spec__.parent` is formerly known as `__package__`.

## Recipe 1: almost hot reloader

This is the smallest recipe, originally invented by [@deathaxe](https://github.com/deathaxe),
and usually good enough for packages without much in-memory state or pending
async callbacks.

```python
import sys

# kiss-reloader:
prefix = __spec__.parent + "."  # don't clear the base package
for module_name in [
    module_name
    for module_name in sys.modules
    if module_name.startswith(prefix) and module_name != __name__
]:
    del sys.modules[module_name]
```

What it does:

- removes your package's submodules from `sys.modules`
- lets Sublime/Python import fresh module objects afterwards
- sees changed source immediately

Why this is only *almost* a hot reloader:

- old functions scheduled via `sublime.set_timeout`, worker threads, event
  handlers, etc. can still be alive
- those old functions still reference the old module globals
- the next import creates new module globals, so old and new code no longer
  share in-memory state

If your package stores app state in module globals, this may split state across
old and new module objects.

## Recipe 2: simple real hot reloader

This keeps module objects alive by reloading them in place.  It is still small
and easy to understand, but it runs module top-level code twice.

```python
import importlib
import sys

# kiss-reloader:
prefix = __spec__.parent + "."  # don't reload the base package
modules = [
    module
    for module_name, module in sys.modules.items()
    if module_name.startswith(prefix) and module_name != __name__
]
for module in modules:
    importlib.reload(module)
for module in modules:
    importlib.reload(module)
```

What happens:

- the first pass executes new source into the existing module objects
- because imports can capture old objects while dependencies are still being
  reloaded, some code can still observe previous objects during that pass
- the second pass executes the source again after dependencies have been
  refreshed, so import-captured names are also fresh

Pros:

- preserves module globals for old callbacks and new code
- sees changed source without needing a second manual reload
- very small

Cons:

- top-level side effects run twice
- if your package refreshes views, starts workers, subscribes callbacks, or runs
  commands at import time, those side effects can happen twice

## Recipe 3: in-place import-hook hot reloader

This is the most complete recipe.  It is larger and harder to understand because
it uses Python import machinery, but it preserves module objects while still
letting imports run normally.

```python
import importlib.abc
import importlib.machinery
import sys
from contextlib import nullcontext
from types import ModuleType


# kiss-reloader
class InPlaceReloader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, modules):
        self.modules = modules
        self.loaders = {}

    def __enter__(self):
        return self.install()

    def __exit__(self, exc_type, exc_value, traceback):
        self.uninstall()

    def install(self):
        for name in self.modules:
            sys.modules.pop(name, None)

        self.clear_parent_module_attributes()
        sys.meta_path.insert(0, self)
        return self

    def uninstall(self):
        if self in sys.meta_path:
            sys.meta_path.remove(self)

    def find_spec(self, fullname, path=None, target=None):
        if fullname not in self.modules:
            return None

        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or spec.loader is None:
            return None

        self.loaders[fullname] = spec.loader
        spec.loader = self
        return spec

    def create_module(self, spec):
        return self.modules[spec.name]

    def exec_module(self, module):
        loader = self.loaders[module.__name__]
        if hasattr(loader, "exec_module"):
            loader.exec_module(module)
        else:
            loader.load_module(module.__name__)  # Python 3.8

    def clear_parent_module_attributes(self):
        for name, module in self.modules.items():
            parent_name, _, attr = name.rpartition(".")
            parent = self.modules.get(parent_name)
            if parent is None:
                parent = sys.modules.get(parent_name)
            if isinstance(parent, ModuleType) and getattr(parent, attr, None) is module:
                delattr(parent, attr)


def reloader(package_name=__spec__.parent, plugin_name=__name__):
    prefix = package_name + "."
    modules = {
        name: module
        for name, module in sys.modules.items()
        if name.startswith(prefix) and name != plugin_name
    }
    return InPlaceReloader(modules) if modules else nullcontext()


with reloader():
    # import your package here ... e.g.
    from .core.commands import *
```

What it does:

- temporarily removes your submodules from `sys.modules`
  like in the first recipe
- clears child-module attributes from parent packages, e.g. `package.core.store`
- intercepts imports for those modules
- returns the old module object from `create_module`
- executes fresh source into that old module object
- falls back to the legacy `load_module()` API for older loaders such as
  Python 3.8's `zipimporter`

Pros:

- old callbacks and new code keep sharing the same module globals
- changed source is visible after one reload
- module top-level code runs once per reload

Cons:

- bigger than the other recipes
- harder to reason about unless you know Python's import machinery

Note: The parent attribute cleanup is important.  Without it, an import such as
`from package.core import store` can reuse `package.core.store` directly from
an already loaded parent package and never ask the import machinery to reload
`package.core.store`.  The `sys.modules` fallback handles direct child imports
such as `from package import core`.  The base package is not in `modules`, but
it still owns those child attributes.

Note: The `reloader()` indirection is another mouthful.  It is not strictly
necessary because `InPlaceReloader({})` would also work with an empty dict.
However, it would add a tiny cost by installing a custom import hook.  The
zero-cost abstraction avoids that cost on initial load/startup.
