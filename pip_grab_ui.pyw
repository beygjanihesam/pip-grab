#!/usr/bin/env python3
"""
pip_grab_ui - download (and install) Python packages through the best working mirror.
Windows: double-click this file (no console window).  Other OS: python pip_grab_ui.pyw
"""
import glob
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

NOWIN = 0x08000000 if os.name == "nt" else 0  # no flashing console windows
CHILD_ENV = {**os.environ, "PIP_GRAB_CHILD": "1"}  # lets a stray copy of this app exit at once


def _m(name, *urls):
    return [[name if i == 0 else f"{name} #{i + 1}", u] for i, u in enumerate(urls)]


# Some mirrors may be down or moved (for the Iranian ones several likely paths are
# listed). "Test mirrors" keeps only the working ones.
DEFAULT_MIRRORS = (
    # ---------- Iran ----------
    _m("Chabokan (Iran)", "https://mirror2.chabokan.net/pypi/simple/",
       "https://mirror.chabokan.net/pypi/simple/")
    + _m("Pardisco (Iran)", "https://mirrors.pardisco.co/pip/simple/",
         "https://mirrors.pardisco.co/pypi/simple/")
    + _m("Runflare (Iran)", "https://mirror-pypi.runflare.com/simple/",
         "https://mirrors.runflare.com/pypi/simple/", "https://mirror.runflare.com/pypi/simple/")
    + _m("Liara (Iran)", "https://package-mirror.liara.ir/repository/pypi/simple/",
         "https://package-mirror.liara.ir/pypi/simple/")
    + _m("ArvanCloud (Iran)", "https://mirror.arvancloud.ir/pypi/simple/",
         "https://mirror.arvancloud.ir/pip/simple/")
    + _m("ITO (Iran)", "https://repo-portal.ito.gov.ir/pypi/simple/",
         "https://repo-portal.ito.gov.ir/repository/pypi/simple/",
         "https://repo-portal.ito.gov.ir/repo/pypi/simple/")
    + _m("Jamko (Iran)", "https://jamko.ir/pypi/simple/", "https://jamko.ir/repository/pypi/simple/",
         "https://jamko.ir/pip/simple/")
    + _m("IranServer (Iran)", "https://mirror.iranserver.com/pypi/simple/",
         "https://mirror.iranserver.com/pypi/web/simple/")
    + _m("MobinHost (Iran)", "https://mirror.mobinhost.com/pypi/simple/",
         "https://mirror.mobinhost.com/pypi/web/simple/")
    + _m("IUT Isfahan (Iran)", "https://repo.iut.ac.ir/pypi/simple/",
         "https://repo.iut.ac.ir/pypi/web/simple/")
    + _m("Shatel (Iran)", "https://mirror.shatel.ir/pypi/simple/")
    + _m("KubarCloud (Iran)", "https://mirrors.kubarcloud.com/pypi/simple/")
    + _m("Faraso (Iran)", "https://mirror.faraso.org/pypi/simple/")
    # ---------- Official ----------
    + _m("PyPI (official)", "https://pypi.org/simple/")
    + _m("PyPI (legacy URL)", "https://pypi.python.org/simple/")
    # ---------- China ----------
    + _m("Tsinghua", "https://pypi.tuna.tsinghua.edu.cn/simple/",
         "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/")
    + _m("Aliyun", "https://mirrors.aliyun.com/pypi/simple/")
    + _m("USTC", "https://pypi.mirrors.ustc.edu.cn/simple/", "https://mirrors.ustc.edu.cn/pypi/web/simple/")
    + _m("Tencent", "https://mirrors.cloud.tencent.com/pypi/simple/", "https://mirrors.tencent.com/pypi/simple/")
    + _m("Huawei", "https://repo.huaweicloud.com/repository/pypi/simple/",
         "https://mirrors.huaweicloud.com/repository/pypi/simple/")
    + _m("Baidu", "https://mirror.baidu.com/pypi/simple/")
    + _m("Douban", "https://pypi.doubanio.com/simple/")
    + _m("Netease", "https://mirrors.163.com/pypi/simple/")
    + _m("Volcengine", "https://mirrors.volces.com/pypi/simple/")
    + _m("NJU", "https://mirror.nju.edu.cn/pypi/web/simple/")
    + _m("SJTUG", "https://mirror.sjtu.edu.cn/pypi/web/simple/", "https://mirrors.sjtug.sjtu.edu.cn/pypi/web/simple/")
    + _m("BFSU", "https://mirrors.bfsu.edu.cn/pypi/web/simple/")
    + _m("ZJU", "https://mirrors.zju.edu.cn/pypi/web/simple/")
    + _m("SUSTech", "https://mirrors.sustech.edu.cn/pypi/web/simple/")
    + _m("LZU", "https://mirror.lzu.edu.cn/pypi/web/simple/")
    + _m("BJTU", "https://mirror.bjtu.edu.cn/pypi/web/simple/")
    + _m("Neusoft", "https://mirrors.neusoft.edu.cn/pypi/web/simple/")
    + _m("HUST", "https://mirrors.hust.edu.cn/pypi/web/simple/")
    + _m("CQU", "https://mirrors.cqu.edu.cn/pypi/web/simple/")
    + _m("PKU", "https://mirrors.pku.edu.cn/pypi/web/simple/")
    + _m("CERNET (China universities)", "https://mirrors.cernet.edu.cn/pypi/web/simple/")
    + _m("OpenCAS", "https://pypi.mirrors.opencas.cn/simple/")
)

CATALOG = {
    "Data science": "numpy pandas scipy matplotlib seaborn plotly scikit-learn statsmodels sympy openpyxl "
                    "xlsxwriter pyarrow polars jupyter notebook jupyterlab ipython ipykernel bokeh altair "
                    "networkx xgboost lightgbm catboost dask h5py",
    "AI / ML": "torch torchvision torchaudio tensorflow keras transformers datasets tokenizers accelerate "
               "diffusers sentence-transformers openai anthropic langchain langchain-community "
               "llama-index huggingface-hub onnxruntime opencv-python opencv-python-headless pillow "
               "spacy nltk gensim tiktoken gradio streamlit",
    "Web / API": "requests httpx aiohttp urllib3 flask django fastapi uvicorn gunicorn starlette pydantic "
                 "jinja2 beautifulsoup4 lxml scrapy selenium playwright websockets websocket-client "
                 "flask-cors djangorestframework celery redis sqlalchemy alembic psycopg2-binary "
                 "pymysql pymongo",
    "Dev tools": "pip setuptools wheel virtualenv pipenv poetry pipx pyinstaller cython numba black "
                 "flake8 pylint mypy ruff isort pytest pytest-cov tox coverage pre-commit click typer "
                 "rich tqdm colorama python-dotenv pyyaml toml tomli pyperclip psutil paramiko fabric",
    "GUI / games": "PyQt5 PyQt6 PySide6 customtkinter pygame kivy wxPython pyautogui keyboard "
                   "pynput pywin32 pyserial",
    "Bots / chat": "python-telegram-bot telethon aiogram pyrogram discord.py tweepy slack-sdk",
    "Audio / video / images": "moviepy ffmpeg-python pydub librosa soundfile SpeechRecognition pyttsx3 gTTS "
                              "yt-dlp pytube imageio scikit-image qrcode pytesseract easyocr",
    "Security / network": "cryptography pycryptodome pyOpenSSL bcrypt passlib PyJWT scapy python-nmap shodan pysocks",
    "Files / dates": "PyPDF2 pypdf reportlab python-docx python-pptx pdfplumber PyMuPDF xlrd tabulate Faker "
                     "arrow pendulum python-dateutil pytz",
    "Persian": "hazm jdatetime persiantools parsivar python-bidi arabic-reshaper",
}

CUSTOM_FILE = Path.home() / ".pip_grab_mirrors.json"


def load_custom():
    try:
        return json.loads(CUSTOM_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_custom(mirrors):
    known = {m[1] for m in DEFAULT_MIRRORS}
    try:
        CUSTOM_FILE.write_text(json.dumps([m for m in mirrors if m[1] not in known],
                                          ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def split_names(text):
    out = []
    for line in text.replace(",", "\n").splitlines():
        line = line.split("#")[0].strip()
        if line and not line.startswith("-"):
            out.extend(line.split())
    return out


def probe(base):
    start = time.time()
    try:
        req = urllib.request.Request(base.rstrip("/") + "/requests/",
                                     headers={"User-Agent": "pip/24.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            ok = r.status == 200 and len(r.read()) > 500
        return ok, time.time() - start
    except Exception:
        return False, time.time() - start


# ---------- finding installed Pythons ----------
def run_quiet(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore",
                           stdin=subprocess.DEVNULL, timeout=timeout, creationflags=NOWIN, env=CHILD_ENV)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return -1, str(e)


def fix_exe(path):
    return re.sub(r"pythonw(\.exe)?$", lambda m: "python" + (m.group(1) or ""), path, flags=re.I)


def is_alias_stub(path):
    return path.lower().replace("/", "\\").endswith("\\microsoft\\windowsapps\\python.exe") or \
        path.lower().replace("/", "\\").endswith("\\microsoft\\windowsapps\\python3.exe")


def collect_candidates():
    cands, py_default, first_on_path = [], None, None
    home = str(Path.home())
    if os.name == "nt":
        rc, out = run_quiet(["py", "-0p"])
        for line in out.splitlines():
            m = re.search(r"([A-Za-z]:\\.*?python[w]?\.exe)\s*$", line.strip(), re.I)
            if m:
                cands.append(m.group(1))
                if "*" in line.split(m.group(1))[0]:
                    py_default = m.group(1)
        la, ap = os.environ.get("LOCALAPPDATA", ""), os.environ.get("APPDATA", "")
        pf = [os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")]
        pats = [rf"{la}\Programs\Python\Python*\python.exe", rf"{ap}\uv\python\*\python.exe",
                rf"{la}\uv\python\*\python.exe", r"C:\Python*\python.exe",
                rf"{la}\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.*\python.exe",
                rf"{home}\.pyenv\pyenv-win\versions\*\python.exe"]
        pats += [rf"{p}\Python*\python.exe" for p in pf if p]
        for base in (home, la, r"C:\ProgramData"):
            for conda in ("anaconda3", "miniconda3", "Anaconda3", "Miniconda3"):
                pats.append(rf"{base}\{conda}\python.exe")
        for p in pats:
            cands += glob.glob(p)
        names = ["python.exe"]
    else:
        pats = ["/usr/bin/python3*", "/usr/local/bin/python3*", "/opt/homebrew/bin/python3*",
                f"{home}/.pyenv/versions/*/bin/python", f"{home}/.local/share/uv/python/*/bin/python3",
                f"{home}/anaconda3/bin/python", f"{home}/miniconda3/bin/python"]
        for p in pats:
            cands += glob.glob(p)
        names = ["python3", "python"]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        for n in names:
            f = os.path.join(d, n)
            if os.path.isfile(f):
                cands.append(f)
                if n in ("python.exe", "python") and first_on_path is None and not is_alias_stub(f):
                    first_on_path = f
    if not getattr(sys, "frozen", False):  # inside an .exe, sys.executable is the exe itself
        cands.append(fix_exe(sys.executable))
    seen, uniq = set(), []
    for c in cands:
        if is_alias_stub(c) or not os.path.isfile(c):
            continue
        key = os.path.normcase(os.path.realpath(c))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq, py_default, first_on_path


def probe_python(path):
    if os.path.normcase(os.path.realpath(path)) == os.path.normcase(os.path.realpath(sys.executable)):
        return None  # that's this app (inside an .exe), not a Python
    code = ("import sys;print(sys.version.split()[0]);"
            "import importlib.util as u;print(u.find_spec('pip') is not None)")
    rc, out = run_quiet([path, "-c", code], timeout=15)
    lines = out.strip().splitlines()
    if rc == 0 and len(lines) >= 2 and re.match(r"\d+\.\d+", lines[0]):
        return {"ver": lines[0], "pip": lines[1].strip() == "True", "path": path}
    return None


def find_pythons():
    cands, py_default, first = collect_candidates()
    with ThreadPoolExecutor(max_workers=6) as ex:
        found = [r for r in ex.map(probe_python, cands) if r]
    norm = lambda p: os.path.normcase(os.path.realpath(p)) if p else None
    me = norm(fix_exe(sys.executable))
    for r in found:
        n, notes = norm(r["path"]), []
        if n == norm(first):
            notes.append("'python' in cmd")
        if n == norm(py_default):
            notes.append("'py' default")
        if n == me:
            notes.append("running this app")
        r["note"] = ", ".join(notes)
        r["key"] = n
    found.sort(key=lambda r: tuple(int(x) for x in re.findall(r"\d+", r["ver"])[:3]), reverse=True)
    pick = next((i for i, r in enumerate(found) if r["key"] == norm(first)), None)
    if pick is None:
        pick = next((i for i, r in enumerate(found) if r["key"] == norm(py_default)), None)
    if pick is None:
        pick = next((i for i, r in enumerate(found) if r["key"] == me), 0)
    return found, pick


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.mirrors = [m[:] for m in DEFAULT_MIRRORS] + load_custom()
        self.results = {}
        self.pys = []
        self.proc = None
        self.cancel = False
        self.busy = False
        root.title("pip_grab - download & install Python packages")
        root.geometry("1000x960")
        root.minsize(900, 800)
        self.build()
        self.poll()
        self.rescan()

    # ---------- UI ----------
    def build(self):
        pad = {"padx": 10, "pady": 3}
        main = ttk.Frame(self.root, padding=6)
        main.pack(fill="both", expand=True)

        # 1) Libraries
        box = ttk.LabelFrame(main, text=" 1) Libraries - pick from the list and/or type them ")
        box.pack(fill="x", **pad)
        pw = ttk.Frame(box)
        pw.pack(fill="x", padx=8, pady=4)
        left = ttk.Frame(pw)
        left.pack(side="left", fill="both", expand=True)
        sr = ttk.Frame(left)
        sr.pack(fill="x")
        ttk.Label(sr, text="Search:").pack(side="left")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *a: self.fill_catalog())
        ttk.Entry(sr, textvariable=self.search, width=14).pack(side="left", padx=4)
        self.cat = tk.StringVar(value="All")
        cb = ttk.Combobox(sr, textvariable=self.cat, state="readonly", width=20,
                          values=["All"] + list(CATALOG))
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: self.fill_catalog())
        lf = ttk.Frame(left)
        lf.pack(fill="both", expand=True, pady=3)
        self.lb = tk.Listbox(lf, selectmode="extended", height=6, exportselection=False)
        lsb = ttk.Scrollbar(lf, command=self.lb.yview)
        self.lb.config(yscrollcommand=lsb.set)
        lsb.pack(side="right", fill="y")
        self.lb.pack(side="left", fill="both", expand=True)
        self.lb.bind("<Double-Button-1>", lambda e: self.add_selected())
        lr = ttk.Frame(left)
        lr.pack(fill="x")
        ttk.Button(lr, text="Add selected  ->", command=self.add_selected).pack(side="left")
        self.cat_count = tk.StringVar()
        ttk.Label(lr, textvariable=self.cat_count).pack(side="right")

        right = ttk.Frame(pw)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        ttk.Label(right, text="Download list (you can type directly, e.g. numpy==1.26.4):").pack(anchor="w")
        self.names = tk.Text(right, height=6, font=("Consolas", 11))
        self.names.pack(fill="both", expand=True, pady=3)
        r = ttk.Frame(right)
        r.pack(fill="x")
        ttk.Button(r, text="Load requirements.txt", command=self.load_req).pack(side="left")
        ttk.Button(r, text="Clear", command=lambda: self.names.delete("1.0", "end")
                   ).pack(side="left", padx=6)
        self.fill_catalog()

        # 2) Python versions
        pyf = ttk.LabelFrame(main, text=" 2) Python to use - all versions found on this computer ")
        pyf.pack(fill="x", **pad)
        pr = ttk.Frame(pyf)
        pr.pack(fill="x", padx=8, pady=4)
        self.btn_scan = ttk.Button(pr, text="Rescan", command=self.rescan)
        self.btn_scan.pack(side="right", padx=(6, 0))
        pt_frame = ttk.Frame(pr)
        pt_frame.pack(side="left", fill="x", expand=True)
        self.pyt = ttk.Treeview(pt_frame, columns=("v", "p", "n", "path"), show="headings",
                                height=4, selectmode="browse")
        for c, t, w in [("v", "Version", 70), ("p", "pip", 50), ("n", "Notes", 190), ("path", "Path", 560)]:
            self.pyt.heading(c, text=t)
            self.pyt.column(c, width=w)
        psb = ttk.Scrollbar(pt_frame, command=self.pyt.yview)
        self.pyt.config(yscrollcommand=psb.set)
        psb.pack(side="right", fill="y")
        self.pyt.pack(side="left", fill="x", expand=True)
        ttk.Label(pyf, text="Downloads and installs run with the selected Python "
                  "(so files always match it).").pack(anchor="w", padx=8, pady=(0, 4))

        # 3) Destination & options
        opt = ttk.LabelFrame(main, text=" 3) Destination & options ")
        opt.pack(fill="x", **pad)
        r1 = ttk.Frame(opt)
        r1.pack(fill="x", padx=8, pady=4)
        ttk.Label(r1, text="Folder:").pack(side="left")
        self.dest = tk.StringVar(value=str(Path.home() / "pip_downloads"))
        ttk.Entry(r1, textvariable=self.dest).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(r1, text="Browse...", command=self.pick_dir).pack(side="left")
        ttk.Button(r1, text="Open folder", command=self.open_dir).pack(side="left", padx=6)
        r2 = ttk.Frame(opt)
        r2.pack(fill="x", padx=8, pady=(0, 4))
        self.nodeps = tk.BooleanVar(value=False)
        self.inst = tk.BooleanVar(value=True)
        ttk.Checkbutton(r2, text="Install after download", variable=self.inst).pack(side="left")
        ttk.Checkbutton(r2, text="No dependencies", variable=self.nodeps).pack(side="left", padx=12)
        ttk.Label(r2, text="For another system (skips install) - platform:").pack(side="left", padx=(16, 2))
        self.plat = tk.StringVar()
        ttk.Combobox(r2, textvariable=self.plat, width=18,
                     values=["", "win_amd64", "manylinux2014_x86_64", "macosx_11_0_arm64",
                             "macosx_10_9_x86_64"]).pack(side="left")
        ttk.Label(r2, text="python:").pack(side="left", padx=(8, 2))
        self.pyv = tk.StringVar()
        ttk.Combobox(r2, textvariable=self.pyv, width=6,
                     values=["", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]
                     ).pack(side="left")

        # 4) Mirrors
        mf = self.mf = ttk.LabelFrame(main, text=" 4) Mirrors ")
        mf.pack(fill="both", **pad)
        mr = ttk.Frame(mf)
        mr.pack(fill="x", padx=8, pady=4)
        self.btn_test = ttk.Button(mr, text="Test mirrors", command=self.test_clicked)
        self.btn_test.pack(side="left")
        ttk.Button(mr, text="Add", command=self.add_mirror).pack(side="left", padx=6)
        ttk.Button(mr, text="Add many", command=self.add_many).pack(side="left")
        ttk.Button(mr, text="Delete", command=self.del_mirror).pack(side="left", padx=6)
        ttk.Button(mr, text="Set as pip default", command=self.set_default).pack(side="left")
        self.mode = tk.StringVar(value="auto")
        ttk.Radiobutton(mr, text="Auto (fastest first)", variable=self.mode, value="auto"
                        ).pack(side="right")
        ttk.Radiobutton(mr, text="Only selected mirror", variable=self.mode, value="sel"
                        ).pack(side="right", padx=8)
        tf = ttk.Frame(mf)
        tf.pack(fill="x", padx=8, pady=(0, 6))
        self.mt = ttk.Treeview(tf, columns=("n", "s", "t", "u"), show="headings", height=5)
        for c, t, w in [("n", "Name", 190), ("s", "Status", 80), ("t", "Time", 70), ("u", "URL", 520)]:
            self.mt.heading(c, text=t)
            self.mt.column(c, width=w)
        self.mt.tag_configure("ok", foreground="#1a7f37")
        self.mt.tag_configure("bad", foreground="#b42318")
        msb = ttk.Scrollbar(tf, command=self.mt.yview)
        self.mt.config(yscrollcommand=msb.set)
        msb.pack(side="right", fill="y")
        self.mt.pack(side="left", fill="x", expand=True)
        self.fill_mirrors()

        # 5) Run
        act = ttk.Frame(main)
        act.pack(fill="x", **pad)
        self.btn_go = ttk.Button(act, text="Start", command=self.start)
        self.btn_go.pack(side="left")
        self.btn_stop = ttk.Button(act, text="Stop", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=6)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(act, textvariable=self.status).pack(side="right")
        self.bar = ttk.Progressbar(main, mode="determinate")
        self.bar.pack(fill="x", padx=10)

        res = ttk.Panedwindow(main, orient="horizontal")
        res.pack(fill="both", expand=True, **pad)
        self.pt = ttk.Treeview(res, columns=("n", "s"), show="headings", height=6)
        self.pt.heading("n", text="Package")
        self.pt.heading("s", text="Status")
        self.pt.column("n", width=170)
        self.pt.column("s", width=150)
        self.pt.tag_configure("ok", foreground="#1a7f37")
        self.pt.tag_configure("bad", foreground="#b42318")
        res.add(self.pt, weight=1)
        lf2 = ttk.Frame(res)
        self.log = tk.Text(lf2, height=8, state="disabled", font=("Consolas", 9), wrap="word")
        sb = ttk.Scrollbar(lf2, command=self.log.yview)
        self.log.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        res.add(lf2, weight=3)

    def fill_mirrors(self):
        self.mt.delete(*self.mt.get_children())
        self.mf.config(text=f" 4) Mirrors ({len(self.mirrors)}) ")
        for i, (n, u) in enumerate(self.mirrors):
            ok_t = self.results.get(i)
            if ok_t:
                ok, t = ok_t
                self.mt.insert("", "end", iid=str(i), tags=("ok" if ok else "bad"),
                               values=(n, "OK" if ok else "Down", f"{t:.2f}s", u))
            else:
                self.mt.insert("", "end", iid=str(i), values=(n, "-", "", u))

    def fill_pys(self):
        self.pyt.delete(*self.pyt.get_children())
        for i, r in enumerate(self.pys):
            self.pyt.insert("", "end", iid=str(i),
                            values=(r["ver"], "yes" if r["pip"] else "NO", r["note"], r["path"]))

    # ---------- events ----------
    def emit(self, *ev):
        self.q.put(ev)

    def poll(self):
        try:
            while True:
                ev = self.q.get_nowait()
                k = ev[0]
                if k == "log":
                    self.log.config(state="normal")
                    self.log.insert("end", ev[1] + "\n")
                    self.log.see("end")
                    self.log.config(state="disabled")
                elif k == "mirrors":
                    self.fill_mirrors()
                elif k == "pys":
                    self.pys, pick = ev[1], ev[2]
                    self.fill_pys()
                    if self.pys:
                        self.pyt.selection_set(str(pick))
                        self.pyt.see(str(pick))
                    self.btn_scan.config(state="normal")
                    self.status.set(f"Found {len(self.pys)} Python installation(s)")
                elif k == "pkg":
                    self.pt.item(ev[1], values=(self.pt.item(ev[1])["values"][0], ev[2]),
                                 tags=(ev[3],) if len(ev) > 3 else ())
                elif k == "bar":
                    self.bar["value"] = ev[1]
                elif k == "status":
                    self.status.set(ev[1])
                elif k == "busy":
                    self.set_busy(ev[1])
                elif k == "msg":
                    messagebox.showinfo("pip_grab", ev[1])
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def set_busy(self, b):
        self.busy = b
        self.btn_go.config(state="disabled" if b else "normal")
        self.btn_test.config(state="disabled" if b else "normal")
        self.btn_stop.config(state="normal" if b else "disabled")

    # ---------- catalog ----------
    def fill_catalog(self):
        q = self.search.get().strip().lower()
        cat = self.cat.get()
        items = []
        for c, names in CATALOG.items():
            if cat in ("All", c):
                items += names.split()
        items = sorted(set(items), key=str.lower)
        if q:
            items = [i for i in items if q in i.lower()]
        self.lb.delete(0, "end")
        for i in items:
            self.lb.insert("end", i)
        self.cat_count.set(f"{len(items)} items")

    def add_selected(self):
        sel = [self.lb.get(i) for i in self.lb.curselection()]
        have = split_names(self.names.get("1.0", "end"))
        new = [x for x in sel if x not in have]
        if new:
            txt = self.names.get("1.0", "end").rstrip()
            self.names.delete("1.0", "end")
            self.names.insert("1.0", (txt + "\n" if txt else "") + "\n".join(new))

    def load_req(self):
        p = filedialog.askopenfilename(filetypes=[("requirements", "*.txt"), ("All files", "*.*")])
        if p:
            self.names.delete("1.0", "end")
            self.names.insert("1.0", Path(p).read_text(encoding="utf-8", errors="ignore"))

    # ---------- buttons ----------
    def get_py(self):
        sel = self.pyt.selection()
        if sel and int(sel[0]) < len(self.pys):
            return self.pys[int(sel[0])]
        return {"path": fix_exe(sys.executable), "ver": "?", "pip": not getattr(sys, "frozen", False)}

    def rescan(self):
        self.btn_scan.config(state="disabled")
        self.status.set("Scanning for Python installations...")

        def job():
            found, pick = find_pythons()
            self.emit("pys", found, pick)
        threading.Thread(target=job, daemon=True).start()

    def pick_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.dest.set(d)

    def open_dir(self):
        p = Path(self.dest.get())
        p.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(p)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])

    def add_mirror(self):
        url = simpledialog.askstring("Add mirror", "Mirror 'simple' URL (e.g. https://.../simple/):")
        if url and url.strip().startswith("http"):
            name = simpledialog.askstring("Add mirror", "A name for this mirror:") or "Custom"
            self.mirrors.append([name, url.strip()])
            save_custom(self.mirrors)
            self.fill_mirrors()

    def add_many(self):
        win = tk.Toplevel(self.root)
        win.title("Add many mirrors")
        ttk.Label(win, text="One mirror per line:  name|url   or just the url").pack(anchor="w", padx=8, pady=6)
        t = tk.Text(win, width=84, height=12)
        t.pack(padx=8)

        def ok():
            have = {m[1] for m in self.mirrors}
            n = 0
            for line in t.get("1.0", "end").splitlines():
                name, _, url = line.strip().rpartition("|")
                url = url.strip()
                if url.startswith("http"):
                    if not url.endswith("/"):
                        url += "/"
                    if url not in have:
                        self.mirrors.append([name.strip() or url.split("/")[2], url])
                        have.add(url)
                        n += 1
            save_custom(self.mirrors)
            self.fill_mirrors()
            win.destroy()
            messagebox.showinfo("pip_grab", f"{n} mirror(s) added")
        ttk.Button(win, text="Add", command=ok).pack(pady=8)

    def del_mirror(self):
        sel = self.mt.selection()
        if sel:
            del self.mirrors[int(sel[0])]
            save_custom(self.mirrors)
            self.results.clear()
            self.fill_mirrors()

    def set_default(self):
        sel = self.mt.selection()
        if not sel:
            messagebox.showinfo("pip_grab", "Select a mirror in the table first.")
            return
        url = self.mirrors[int(sel[0])][1]
        py = self.get_py()["path"]
        rc, out = run_quiet([py, "-m", "pip", "config", "set", "global.index-url", url])
        messagebox.showinfo("pip_grab", f"(Python {self.get_py()['ver']})\n" + (out.strip() or "Done"))

    def test_clicked(self):
        self.set_busy(True)
        threading.Thread(target=self.test_job, daemon=True).start()

    def stop(self):
        self.cancel = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.emit("status", "Stopping...")

    # ---------- background work ----------
    def probe_all(self):
        self.emit("status", "Testing mirrors...")
        urls = [m[1] for m in self.mirrors]
        with ThreadPoolExecutor(max_workers=24) as ex:
            out = list(ex.map(probe, urls))
        self.results = dict(enumerate(out))
        self.emit("mirrors")
        good = [i for i, (ok, _) in self.results.items() if ok]
        good.sort(key=lambda i: self.results[i][1])
        return good

    def test_job(self):
        good = self.probe_all()
        self.emit("status", f"{len(good)} working mirror(s) out of {len(self.mirrors)}")
        self.emit("busy", False)

    def start(self):
        pk = split_names(self.names.get("1.0", "end"))
        if not pk:
            messagebox.showinfo("pip_grab", "No libraries entered.")
            return
        if not self.pys:
            messagebox.showwarning(
                "pip_grab", "No Python installation was found on this computer.\n\n"
                "Install Python from python.org (tick 'Add python.exe to PATH'), "
                "then press Rescan.")
            return
        py = self.get_py()
        if not py["pip"]:
            messagebox.showwarning("pip_grab", "The selected Python has no pip. Choose another one.")
            return
        self.pt.delete(*self.pt.get_children())
        for i, p in enumerate(pk):
            self.pt.insert("", "end", iid=str(i), values=(p, "Queued"))
        sel = self.mt.selection()
        opts = dict(
            dest=self.dest.get().strip() or "downloads",
            nodeps=self.nodeps.get(), install=self.inst.get(),
            plat=self.plat.get().strip(), pyv=self.pyv.get().strip(),
            only=int(sel[0]) if (self.mode.get() == "sel" and sel) else None,
            py=py["path"], pyver=py["ver"],
        )
        self.cancel = False
        self.bar.config(maximum=len(pk), value=0)
        self.set_busy(True)
        threading.Thread(target=self.download_job, args=(pk, opts), daemon=True).start()

    def run(self, cmd):
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, text=True,
                                     encoding="utf-8", errors="ignore", creationflags=NOWIN,
                                     env=CHILD_ENV)
        out, _ = self.proc.communicate()
        return self.proc.returncode, (out or "").strip()

    def download_job(self, pk, o):
        py, dest = o["py"], Path(o["dest"])
        self.emit("log", f"Using Python {o['pyver']}  ({py})")
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.emit("log", f"Could not create folder: {e}")
            self.emit("busy", False)
            return
        order = [o["only"]] if o["only"] is not None else self.probe_all()
        if not order:
            self.emit("log", "No working mirror found. Check your internet connection or the URLs.")
            self.emit("status", "Failed")
            self.emit("busy", False)
            return
        failed, other_target = [], bool(o["plat"] or o["pyv"])
        for idx, pkg in enumerate(pk):
            if self.cancel:
                break
            self.emit("pkg", str(idx), "Downloading...")
            self.emit("status", f"{pkg}  ({idx + 1}/{len(pk)})")
            done = False
            for mi in order:
                if self.cancel:
                    break
                name, base = self.mirrors[mi]
                self.emit("log", f"[{pkg}] from {name} ...")
                cmd = [py, "-m", "pip", "download", pkg, "-d", str(dest),
                       "--index-url", base, "--timeout", "20", "--retries", "1",
                       "--disable-pip-version-check"]
                if o["nodeps"]:
                    cmd.append("--no-deps")
                if o["plat"]:
                    cmd += ["--platform", o["plat"]]
                if o["pyv"]:
                    cmd += ["--python-version", o["pyv"]]
                if other_target:
                    cmd.append("--only-binary=:all:")
                code, out = self.run(cmd)
                if code == 0:
                    self.emit("log", f"  OK downloaded ({name})")
                    done = True
                    break
                last = out.splitlines()[-1] if out else "unknown error"
                self.emit("log", f"  FAILED: {last}")
            if done:
                self.emit("pkg", str(idx), "Downloaded", "ok")
            else:
                if not self.cancel:
                    failed.append(pkg)
                self.emit("pkg", str(idx), "Failed" if not self.cancel else "Cancelled", "bad")
            self.emit("bar", idx + 1)

        if self.cancel:
            self.emit("status", "Stopped")
        elif failed:
            self.emit("status", f"{len(failed)} failed")
            self.emit("log", "Failed: " + ", ".join(failed))
        else:
            self.emit("status", "All downloaded")
            if o["install"] and not other_target:
                self.install_and_verify(pk, dest, o)
            elif o["install"]:
                self.emit("log", "\nInstall skipped: files were downloaded for another system.")
            self.emit("log", f"\nFolder: {dest.resolve()}\nTo install on another machine:\n"
                             f"pip install --no-index --find-links=\"{dest}\" " + " ".join(pk))
        self.emit("busy", False)

    def install_and_verify(self, pk, dest, o):
        py = o["py"]
        self.emit("status", "Installing...")
        self.emit("log", f"\nInstalling with Python {o['pyver']} ...")
        code, out = self.run([py, "-m", "pip", "install", "--no-index", "--find-links", str(dest),
                              "--disable-pip-version-check"] + pk)
        self.emit("log", out[-700:])
        if code != 0:
            self.emit("status", "Install failed (see log)")
            for i in range(len(pk)):
                self.emit("pkg", str(i), "Install failed", "bad")
            return
        self.emit("log", "\nVerifying installation:")
        bad = 0
        for i, pkg in enumerate(pk):
            base = re.split(r"[=<>!~\[;@ ]", pkg)[0]
            rc, info = run_quiet([py, "-m", "pip", "show", base])
            ver = re.search(r"^Version:\s*(.+)$", info, re.M)
            loc = re.search(r"^Location:\s*(.+)$", info, re.M)
            if rc == 0 and ver:
                self.emit("log", f"  OK  {base} {ver.group(1).strip()}  ->  {loc.group(1).strip() if loc else ''}")
                self.emit("pkg", str(i), f"Installed {ver.group(1).strip()}", "ok")
            else:
                bad += 1
                self.emit("log", f"  MISSING  {base}")
                self.emit("pkg", str(i), "Not installed", "bad")
        self.emit("status", f"Installed on Python {o['pyver']}" if not bad else f"{bad} not installed")


def single_instance():
    """Hold a local port as a lock; a second copy of the app can't get it."""
    import socket
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 49731))
        sock.listen(1)
        return sock
    except OSError:
        return None


def main():
    if os.environ.get("PIP_GRAB_CHILD"):
        sys.exit(0)
    lock = single_instance()
    if lock is None:
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo("pip_grab", "pip_grab is already running.")
        sys.exit(0)
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista" if os.name == "nt" else "clam")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
