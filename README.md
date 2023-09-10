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