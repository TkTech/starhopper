# Starhopper

Starhopper is a tool for extracting data from Bethesda's Starfield game. It:

- Provides a low level Python library for reading the game's data files.
- Provides a Qt-based GUI for exploring the game's data files.

This tool is currently in _early_ development. The game quite literally just
got released.


## Getting It

There's no reason binary releases can't be made for this project. It works on
Linux, Windows, and Mac. However, it's not yet at a stage where that is
worthwhile.

In the meantime, you can get it from pypi:

```bash
pip install starhopper
```

And if you want the GUI:

```bash
pip install starhopper[gui]
```

## Support

This project is brand new and everything is from scratch, so compatibility is
an ongoing effort. If you have a file that doesn't work, please open an issue
and attach the file. I'll try to get it working as soon as possible.

Right now, the project is only tested against Starfield. Patches for older
Bethesda games are welcome.

Included parsers:

| Format   | Version(s) | Note                                                  |
|----------|------------|-------------------------------------------------------|
| ESM      | TES5       | Raw viewer, only a few Records have detailed support. |
| .ba2     | v2, v3     | GNRL records only, DX10 not yet supported.            |
| .strings | All        | Supports .strings, .dlstrings, and .ilstrings.        |
| .mesh    | All(?)     | Supports enough to export .obj files.                 |
