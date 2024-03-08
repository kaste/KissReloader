# KissReloader

The plugin packages a new simplified reloader, originally invented by [@deathaxe](https://github.com/deathaxe).

Choose `kiss-reload: Reload Current Package` from the Command Palette to reload
the plugin you're currently looking at.

There is also an `ApplicationCommand` to reload a specific package at will, e.g.:

```json5
    {
        "command": "kiss_reloader_reload",
        "args": {"package_name": "GitSavvy"}
    },
```

# Add the reloader to your package

You may want to add reloader code to your main/root plugin so it actually reloads
automatically if Package Control gets an update.  Just add this to your plugin:

```python
import sys

# kiss-reloader:
prefix = __package__ + "."  # don't clear the base package
for module_name in [
    module_name
    for module_name in sys.modules
    if module_name.startswith(prefix) and module_name != __name__
]:
    del sys.modules[module_name]
```

`KissReloader` will watch out for the conventional "# kiss-reloader:" comment
and prevent a double reload.
