# pip_grab

**Download and install Python packages through the fastest working PyPI mirror.**

[فارسی](README.fa.md)

pip_grab is a small desktop app (Tkinter, no third-party dependencies) for people whose
connection to PyPI is slow, unreliable, or blocked. You pick the libraries, it tests a
large list of mirrors, downloads from the fastest one that works, and installs the result
into the Python version you choose.

## Why I built this

If you've used Python from Iran, you know the routine: you run `pip install`, nothing
happens for minutes, then you get a timeout. You try another mirror and that one is down
too. An hour later you're still testing URLs by hand.

I got tired of that, so I built pip_grab. It tests the mirrors for you, picks the fastest
one that works, and moves on to the next if one fails, so all you do is type the package
name. You can also download the files once and carry them to an offline computer.

This is my first open-source project. If you know a working mirror or find a bug, please
open an issue or a pull request.

## Requirements

- Python 3.8 or newer **with Tkinter** (the python.org installer includes it)
- Internet access (for downloading)
- Built and tested on Windows. It should also run on macOS and Linux, but it has had much
  less testing there.

pip_grab does not bundle pip. It runs pip from the Python installations already on your
computer, which is how you can choose which one to install into.

## Quick start

```
python pip_grab_ui.pyw
```

On Windows you can also double-click `pip_grab_ui.pyw` (no console window appears).

1. Pick or type the libraries you want.
2. Check which Python is selected.
3. Press **Start**.

That's it. The rest of this page explains every part of the window.

## Using the app

The window has four sections, then the Start button, a progress bar, a results table
and a log.

### 1) Libraries

- **Search box / category list:** filter the built-in list of ~180 popular packages
  (data science, AI/ML, web, dev tools, GUI, bots, audio/video, security, files, Persian).
- **Select packages:** click one, or hold Ctrl / Shift to select several, then press
  **Add selected**. Double-clicking a package adds it too.
- **Download list (right side):** this is what will actually be downloaded. You can type
  in it directly, one name per line or separated by spaces/commas. Version pins work:
  `numpy==1.26.4`, `requests>=2.31`. Anything after `#` on a line is ignored.
- **Load requirements.txt:** fills the list from a requirements file (lines starting
  with `-` are skipped).
- **Clear:** empties the list.

You can mix both ways: add a few from the list, then type extra ones.

### 2) Python to use

The app scans your computer and lists every Python it finds: the `py` launcher, folders on
your PATH, the usual install locations (python.org, Microsoft Store, uv, Anaconda,
Miniconda, pyenv), and so on.

| Column | Meaning |
|---|---|
| Version | Python version |
| pip | `yes` if that Python has pip, `NO` if not (it can't be used) |
| Notes | `'python' in cmd` = what typing `python` in a terminal runs; `'py' default` = what the `py` launcher runs |
| Path | Full path to that `python.exe` |

Click the row you want. **Everything (downloads, installs, verification) runs with the
selected Python**, so the downloaded files always match it. Use **Rescan** after
installing a new Python.

**Why this matters:** many people have several Pythons. A package installed into one is
invisible to another, which causes `ModuleNotFoundError` even though the install
"succeeded". By default the app selects the one that `python` runs in your terminal.

### 3) Destination & options

- **Folder:** where the downloaded files (`.whl` / `.tar.gz`) are saved. Default is
  `pip_downloads` in your user folder. **Browse...** picks another folder, **Open folder**
  opens it.
- **Install after download** (on by default): installs the downloaded files into the
  selected Python, then checks each package with `pip show` and marks it
  "Installed <version>" in the results table. Turn it off if you only want the files.
- **No dependencies:** downloads only the packages you listed, not what they depend on.
  Leave it off unless you know you want that.
- **For another system (skips install):** fill in **platform** and/or **python** to
  download files for a *different* computer, for example a Windows machine with
  Python 3.11:
  - platform: `win_amd64`, `manylinux2014_x86_64`, `macosx_11_0_arm64`, `macosx_10_9_x86_64`
  - python: `3.8` ... `3.14`

  Only prebuilt wheels are downloaded in this mode, and nothing is installed on your own
  computer.

### 4) Mirrors

A mirror is an alternative server that carries the same packages as PyPI. The app comes
with 55 built-in mirrors: Iranian ones, the official PyPI addresses, and many Chinese
university/company mirrors.

- **Test mirrors:** checks all of them in parallel. Working ones turn green (`OK`) with
  their response time, dead ones turn red (`Down`).
- **Auto (fastest first)** (default): when you press Start, mirrors are tested and tried
  from fastest to slowest. If one fails for a package, the next one is used.
- **Only selected mirror:** select a row in the table and use only that mirror.
- **Add / Add many:** add your own mirrors. For *Add many*, put one per line as
  `name|url` or just the URL. The URL must be the pip "simple" index, e.g.
  `https://example.com/pypi/simple/`.
- **Delete:** removes the selected mirror from the list.
- **Set as pip default:** runs `pip config set global.index-url <mirror>` for the
  selected Python, so plain `pip install` in your terminal uses that mirror from now on.

Mirrors you add are saved in `~/.pip_grab_mirrors.json` and come back next time.

### Start, Stop and results

- **Start** begins the job. **Stop** cancels it.
- The **results table** shows each package: `Queued`, `Downloading...`, `Downloaded`,
  `Installed <version>`, `Failed`, or `Install failed`.
- The **log** shows which mirror was tried for each package and why a try failed.
  After a successful run it also prints the command to install the same files on another
  computer:
  ```
  pip install --no-index --find-links="C:\path\to\pip_downloads" numpy
  ```

## Common workflows

**Install a few libraries on this PC**
Pick them in section 1, check section 2, press Start. Done.

**Prepare packages for an offline computer**
1. On a computer with internet, add the libraries, turn **Install after download** off
   (or fill platform/python for the other PC), and press Start.
2. Copy the whole download folder to the offline computer (USB stick).
3. There, run: `pip install --no-index --find-links="<folder>" numpy`

**Make plain `pip install` use a working mirror**
Press **Test mirrors**, select a green one, press **Set as pip default**.

## Troubleshooting

**"Successfully installed", but `import x` fails.**
You installed into a different Python than the one you run. Look at the *Python to use*
table and the *Notes* column; select the one marked `'python' in cmd`, or run your
script with the Python you installed into.

**All mirrors show `Down`.**
Check your internet connection. Some networks block certain mirrors; try again later or
add mirrors that work for you. Mirror URLs change often, and some Iranian ones are
listed with several likely paths because the exact path isn't always documented, so
some failures are expected.

**"No Python installation was found."**
Install Python from python.org (tick "Add python.exe to PATH"), then press **Rescan**.

**"The selected Python has no pip."**
Choose another row, or install pip for that Python: `python -m ensurepip`.

**A package fails on every mirror.**
Check the name and version spelling (the log shows pip's error). Some packages with
compiled code have no prebuilt file for very new Python versions; pick an older Python
in section 2.

**"pip_grab is already running."**
Only one copy can run at a time. Close the other window.

## Safety notes

- Mirrors are third-party servers. Only use mirrors you trust, because packages from an
  untrusted mirror could contain malicious code.
- The app contains no telemetry. It only connects to the mirror servers you test or use.

## Contributing

Working mirror URLs are the most useful contribution. They move and go down often. Open
an issue or a pull request with the URL, and which country/network you tested it from.
Bug reports are welcome too.

## License

MIT - see [LICENSE](LICENSE).
