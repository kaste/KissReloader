# KissReloader

The plugin packages a new simplified reloader, originally invented by [@deathaxe](https://github.com/deathaxe).

Choose `kiss-reload: Reload Current Package` from the Command Palette to reload
the plugin you're currently looking at.

There is also an `ApplicationCommand` to reload a specific package at will, e.g.:

```
    {
        "command": "kiss_reloader_reload",
        "args": {"package_name": "GitSavvy"}
    },
```

