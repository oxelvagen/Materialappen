
# Materialappen — Full funktionalitet + produktbilder (FIX)
import os, sys, csv, json, platform, subprocess, time, shutil, ctypes, winreg
from ctypes import wintypes
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, datetime

from PySide6.QtWidgets import (
    QApplication, QMessageBox, QWidget, QMainWindow, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QListWidget, QLineEdit, QComboBox,
    QHeaderView, QLabel, QStatusBar, QInputDialog, QFileDialog, QPushButton
)
from PySide6.QtCore import QFile, QIODevice, Qt, QTimer, QSize
from PySide6.QtGui import QIcon, QPixmap, QFont, QFontInfo
from PySide6.QtUiTools import QUiLoader

APP_NAME = "Materialappen"
DATA_DIR = "data"
REPORTS_DIR = "reports"
ASSETS_DIR = "assets/icons"
PRODUCT_IMG_DIR = "assets/product_images"
QSS_PATH = "assets/qss/win11.qss"
APP_ICON = "icon.png"

DEFAULT_MUNICIPALITIES = ["Nora", "Lindesberg", "Hällefors", "Ljusnarsberg"]
DEFAULT_USERS = ["Andreas", "Kollega"]
DEFAULT_MATERIALS = [
    {"id":"7778234","label":"Fundament 108/900","description":"FUNDAMENT MEAG 108/900","unit":"st","favorite":True},
    {"id":"7779866","label":"Stolpinsats (komplett)","description":"Stolpinsats","unit":"st","favorite":True},
    {"id":"cw25-k1","label":"Armatur CW-25 (klass1, jordad)","description":"","unit":"st","favorite":False},
]

def is_frozen() -> bool:
    return getattr(sys, "frozen", False)

def bundle_dir() -> Path:
    # Where we READ bundled resources when frozen
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent

def run_dir() -> Path:
    # Where we WRITE runtime data (next to the .exe when frozen, or next to this .py)
    return (Path(sys.executable).resolve().parent if is_frozen() else Path(__file__).resolve().parent)

def script_dir() -> Path:
    # Backwards compat: places that previously read from script_dir should read from bundle when frozen
    return bundle_dir()
def assets_path() -> Path:
    # READ-ONLY assets from bundle (qss, icons)
    return bundle_dir() / "assets"
def icon_path() -> Path:
    return assets_path() / "icons" / APP_ICON
def product_img_dir() -> Path:
    # WRITEABLE product images next to exe
    p = run_dir() / PRODUCT_IMG_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p
def app_icon() -> QIcon:
    p = icon_path(); return QIcon(str(p)) if p.exists() else QIcon()
    p = icon_path(); return QIcon(str(p)) if p.exists() else QIcon()

def get_windows_accent_hex() -> Optional[str]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as k:
            val, _ = winreg.QueryValueEx(k, "ColorizationColor")
            rgb = val & 0xFFFFFF
            return f"#{rgb:06x}"
    except Exception:
        return None

def hex_to_rgb_tuple(hexstr: str) -> Tuple[int,int,int]:
    hexstr = hexstr.lstrip("#")
    return int(hexstr[0:2],16), int(hexstr[2:4],16), int(hexstr[4:6],16)

def enable_win11_effects(hwnd: int, dark: bool = False):
    if platform.system() != "Windows": return
    try:
        dwmapi = ctypes.windll.dwmapi
        HWND = wintypes.HWND; DWORD = wintypes.DWORD
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWA_SYSTEMBACKDROP_TYPE     = 38
        DWMWCP_ROUND = 2
        DWMSBT_MAINWINDOW = 2  # Mica
        val = DWORD(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(HWND(hwnd), DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE), ctypes.byref(val), ctypes.sizeof(val))
        corner = DWORD(DWMWCP_ROUND)
        dwmapi.DwmSetWindowAttribute(HWND(hwnd), DWORD(DWMWA_WINDOW_CORNER_PREFERENCE), ctypes.byref(corner), ctypes.sizeof(corner))
        backdrop = DWORD(DWMSBT_MAINWINDOW)
        dwmapi.DwmSetWindowAttribute(HWND(hwnd), DWORD(DWMWA_SYSTEMBACKDROP_TYPE), ctypes.byref(backdrop), ctypes.sizeof(backdrop))
    except Exception:
        pass

# ---------------------------- persistence ----------------------------
@dataclass
class Material:
    id: str; label: str; description: str; unit: str; favorite: bool=False
    def to_json(self)->Dict[str,Any]: return asdict(self)
    @staticmethod
    def from_json(d:Dict[str,Any])->"Material":
        return Material(id=str(d.get("id","")),label=str(d.get("label","")),description=str(d.get("description","")),unit=str(d.get("unit","st")),favorite=bool(d.get("favorite",False)))

@dataclass
class Entry:
    id:str; user:str; municipality:str; materialId:str; materialLabel:str; qty:float; unit:str; date:str
    def to_json(self)->Dict[str,Any]: return asdict(self)

class Data:
    def __init__(self, base:Path):
        self.data_dir = base / DATA_DIR; self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir = base / REPORTS_DIR; self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.p_mats = self.data_dir / "materials.json"
        self.p_entries = self.data_dir / "entries.json"
        self.p_munis = self.data_dir / "municipalities.json"
        self.p_users = self.data_dir / "users.json"
        # Initialize with defaults if empty files don't exist
        if not self.p_mats.exists(): self.p_mats.write_text(json.dumps(DEFAULT_MATERIALS, ensure_ascii=False, indent=2), encoding="utf-8")
        if not self.p_entries.exists(): self.p_entries.write_text("[]", encoding="utf-8")
        if not self.p_munis.exists(): self.p_munis.write_text(json.dumps(DEFAULT_MUNICIPALITIES, ensure_ascii=False, indent=2), encoding="utf-8")
        if not self.p_users.exists(): self.p_users.write_text(json.dumps(DEFAULT_USERS, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read(self, p:Path, default):
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: return default
    def _write(self, p:Path, data): p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def materials(self)->List[Material]: return [Material.from_json(x) for x in self._read(self.p_mats, [])]
    def save_materials(self, mats:List[Material]): self._write(self.p_mats, [m.to_json() for m in mats])

    def entries(self)->List[Entry]:
        return [Entry(**x) if isinstance(x, dict) else x for x in self._read(self.p_entries, [])]
    def save_entries(self, es:List[Entry]): self._write(self.p_entries, [e.to_json() for e in es])

    def munis(self)->List[str]: return list(self._read(self.p_munis, []))
    def save_munis(self, xs:List[str]): self._write(self.p_munis, xs)

    def users(self)->List[str]: return list(self._read(self.p_users, []))
    def save_users(self, xs:List[str]): self._write(self.p_users, xs)

    def create_csv(self, entries:List[Entry])->Path:
        headers = ["Datum","Användare","Kommun","Material","Antal","Enhet"]
        ts=datetime.now().strftime("%Y%m%d-%H%M%S")
        out=self.reports_dir / f"report-{ts}.csv"
        with out.open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f, delimiter=";")
            w.writerow(headers)
            for e in entries:
                w.writerow([e.date,e.user,e.municipality,e.materialLabel,f"{e.qty:g}",e.unit])
        return out

    def create_pdf(self, title:str, rows:List[Tuple[str,str,str]])->Path:
        def esc(s:str)->str: return s.replace("\\","\\\\").replace("(","\\(").replace(")","\\)")
        y=800; lines=[]
        lines.append(f"BT /F1 16 Tf 50 {y} Td ({esc(title)}) Tj ET"); y-=24
        lines.append(f"BT /F1 10 Tf 50 {y} Td (Genererad: {datetime.now().strftime('%Y-%m-%d %H:%M')}) Tj ET"); y-=18
        cur=None
        for muni, txt, _ in rows:
            if muni!=cur:
                cur=muni; y-=10; lines.append(f"BT /F1 12 Tf 50 {y} Td ({esc('Kommun: '+str(muni))}) Tj ET"); y-=18
            lines.append(f"BT /F1 10 Tf 66 {y} Td ({esc(txt)}) Tj ET"); y-=14
        stream=("\n".join(lines)).encode("cp1252","replace")

        objs=[]
        def add(b:bytes)->int: objs.append(b); return len(objs)
        font=add(b"<< /Type /Font /Subtype /Type1 /Name /F1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        content=add(b"<< /Length %d >>\nstream\n"%len(stream) + stream + b"\nendstream")
        page=add(b"<< /Type /Page /Parent 4 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"%(font,content))
        pages=add(b"<< /Type /Pages /Kids [ %d 0 R ] /Count 1 >>"%(page))
        catalog=add(b"<< /Type /Catalog /Pages 4 0 R >>")

        buf=bytearray(); buf.extend(b"%PDF-1.4\n"); offs=[0]
        for i,obj in enumerate(objs, start=1):
            offs.append(len(buf)); buf.extend(f"{i} 0 obj\n".encode()); buf.extend(obj); buf.extend(b"\nendobj\n")
        xref=len(buf); n=len(objs)+1
        buf.extend(f"xref\n0 {n}\n".encode()); buf.extend(b"0000000000 65535 f \n")
        for off in offs[1:]: buf.extend(f"{off:010d} 00000 n \n".encode())
        buf.extend(b"trailer\n"); buf.extend(f"<< /Size {n} /Root {catalog} 0 R >>\n".encode())
        buf.extend(f"startxref\n{xref}\n%%EOF\n".encode())
        ts=datetime.now().strftime("%Y%m%d-%H%M%S"); out=self.reports_dir / f"rapport-{ts}.pdf"
        with out.open("wb") as f: f.write(buf)
        return out

# ---------------------------- UI loader ----------------------------
def find_ui_file() -> Optional[Path]:
    for p in [bundle_dir() / "ui" / "main.ui", Path.cwd() / "ui" / "main.ui", script_dir() / "ui" / "main.ui"]:
        if p.is_file(): return p
    return None

def load_ui() -> QWidget:
    p = find_ui_file()
    if not p: QMessageBox.critical(None,"Fel","Hittar inte ui/main.ui"); sys.exit(1)
    loader=QUiLoader(); qf=QFile(str(p))
    if not qf.open(QIODevice.ReadOnly):
        QMessageBox.critical(None,"Fel","Kunde inte läsa ui/main.ui"); sys.exit(1)
    try: w=loader.load(qf)
    finally: qf.close()
    if w is None:
        QMessageBox.critical(None,"Fel","Qt kunde inte ladda UI."); sys.exit(1)
    return w

# ---------------------------- controller ----------------------------
class App:
    def __init__(self):
        self.d = Data(run_dir())
        self.w = load_ui()
        # Ensure window size
        try:
            if isinstance(self.w,(QMainWindow,QWidget)):
                self.w.resize(QSize(1200,700))
                self.w.setMinimumSize(QSize(1200,700))
                self.w.setWindowTitle(APP_NAME)
        except Exception:
            pass

        # App icon
        ic = app_icon()
        if not ic.isNull():
            QApplication.instance().setWindowIcon(ic)
            if isinstance(self.w, QMainWindow): self.w.setWindowIcon(ic)

        # Win 11 visual polish
        if platform.system() == "Windows":
            try: enable_win11_effects(int(self.w.winId()), dark=False)
            except Exception: pass

        # Font: try Segoe UI Variable -> Segoe UI
        test = QFont("Segoe UI Variable", 10)
        QApplication.instance().setFont(test)
        if "segoe" not in QFontInfo(test).family().lower():
            QApplication.instance().setFont(QFont("Segoe UI", 10))

        # Accent-aware QSS
        self._apply_qss()

        # Bind widgets
        self.editDate = getattr(self.w,'editDate',None)
        self.comboUser = getattr(self.w,'comboUser',None)
        self.comboMunicipality = getattr(self.w,'comboMunicipality',None)
        self.comboMaterial = getattr(self.w,'comboMaterial',None)
        self.editQty = getattr(self.w,'editQty',None)
        self.btnAddEntry = getattr(self.w,'btnAddEntry',None)
        self.tableEntries = getattr(self.w,'tableEntries',None)
        self.btnDeleteSelected = getattr(self.w,'btnDeleteSelected',None)
        self.btnClearAll = getattr(self.w,'btnClearAll',None)
        self.btnQuickPdf = getattr(self.w,'btnQuickPdf',None)

        self.listMaterials = getattr(self.w,'listMaterials',None)
        self.editMunit = getattr(self.w,'editMunit',None)
        self.btnMatAddUpdate = getattr(self.w,'btnMatAddUpdate',None)
        self.btnMatDelete = getattr(self.w,'btnMatDelete',None)
        self.btnMatEditId = getattr(self.w,'btnMatEditId',None)
        self.btnAddImage: QPushButton = getattr(self.w,'btnAddImage',None)
        self.previewImage: QLabel = getattr(self.w,'previewImage',None)

        self.listMunis = getattr(self.w,'listMunis',None)
        self.editNewMuni = getattr(self.w,'editNewMuni',None)
        self.btnMuniAdd = getattr(self.w,'btnMuniAdd',None)
        self.btnMuniDelete = getattr(self.w,'btnMuniDelete',None)

        self.listUsers = getattr(self.w,'listUsers',None)
        self.editNewUser = getattr(self.w,'editNewUser',None)
        self.btnUserAdd = getattr(self.w,'btnUserAdd',None)
        self.btnUserDelete = getattr(self.w,'btnUserDelete',None)

        self.editFrom = getattr(self.w,'editFrom',None)
        self.editTo = getattr(self.w,'editTo',None)
        self.comboUserF = getattr(self.w,'comboUserF',None)
        self.comboMuniF = getattr(self.w,'comboMuniF',None)
        self.comboMatF = getattr(self.w,'comboMatF',None)
        self.btnMakeCsv = getattr(self.w,'btnMakeCsv',None)
        self.btnMakePdf = getattr(self.w,'btnMakePdf',None)
        self.listReports = getattr(self.w,'listReports',None)
        self.btnOpenReport = getattr(self.w,'btnOpenReport',None)
        self.btnDeleteReport = getattr(self.w,'btnDeleteReport',None)

        # Statusbar
        self.status = None
        if isinstance(self.w, QMainWindow):
            sb = self.w.statusBar() or QStatusBar(self.w)
            self.w.setStatusBar(sb); self.status = sb

        # Data
        self.materials: List[Material] = self.d.materials()
        self.entries: List[Entry] = self.d.entries()
        self.munis: List[str] = self.d.munis()
        self.users: List[str] = self.d.users()

        self._init_ui()
        self._wire()

        if isinstance(self.w,(QMainWindow,QWidget)):
            self.w.setWindowTitle(APP_NAME)

    # ---------- visuals ----------
    def _apply_qss(self):
        qss_file = bundle_dir() / QSS_PATH
        if not qss_file.exists(): return
        qss = qss_file.read_text(encoding="utf-8")
        accent = get_windows_accent_hex() or "#2563eb"
        r,g,b = hex_to_rgb_tuple(accent)
        qss = qss.replace("{ACCENT}", accent).replace("{ACCENT_RGB}", f"{r},{g},{b}")
        QApplication.instance().setStyleSheet(qss)

    def _status(self, msg: str, msec: int = 2000):
        if self.status: self.status.showMessage(msg, msec)

    def _set_items(self, combo: Optional[QComboBox], items: List[str]):
        if not combo: return
        combo.clear(); combo.addItems(items)

    def _init_ui(self):
        # Date default
        today = date.today().isoformat()
        if isinstance(getattr(self.w,'editDate',None), QLineEdit) and not self.w.editDate.text().strip():
            self.w.editDate.setText(today)

        # Fill combos
        self._set_items(self.comboUser, self.users)
        self._set_items(self.comboMunicipality, self.munis)
        if self.comboMaterial:
            self.comboMaterial.clear()
            for m in self.materials:
                self.comboMaterial.addItem(m.label, userData=m.id)

        # Reports combos (if present)
        if self.comboUserF:
            self.comboUserF.clear(); self.comboUserF.addItem("Alla"); self.comboUserF.addItems(self.users)
        if self.comboMuniF:
            self.comboMuniF.clear(); self.comboMuniF.addItem("Alla"); self.comboMuniF.addItems(self.munis)
        if self.comboMatF:
            self.comboMatF.clear(); self.comboMatF.addItem("Alla"); self.comboMatF.addItems([m.label for m in self.materials])

        # Table visuals
        if isinstance(self.tableEntries, QTableWidget):
            self.tableEntries.setAlternatingRowColors(True)
            self.tableEntries.setWordWrap(True)
            hh: QHeaderView = self.tableEntries.horizontalHeader()
            vh: QHeaderView = self.tableEntries.verticalHeader()
            if hh:
                hh.setStretchLastSection(True)
                hh.setSectionResizeMode(QHeaderView.Stretch)
                # Set specific widths for first three columns via resize
                try:
                    hh.setSectionResizeMode(0, QHeaderView.Interactive)
                    hh.setSectionResizeMode(1, QHeaderView.Interactive)
                    hh.setSectionResizeMode(2, QHeaderView.Interactive)
                    self.tableEntries.setColumnWidth(0, 120)
                    self.tableEntries.setColumnWidth(1, 150)
                    self.tableEntries.setColumnWidth(2, 180)
                except Exception:
                    pass
            if vh: vh.setVisible(False)

        # Populate
        self._refresh_entries_table()
        self._refresh_materials_list()
        self._refresh_muni_list()
        self._refresh_user_list()
        self._refresh_reports_list()

        # Autosize on resize
        if isinstance(self.w, QWidget) and isinstance(self.tableEntries, QTableWidget):
            old = self.w.resizeEvent
            def handler(event):
                if callable(old): old(event)
                QTimer.singleShot(0, self._autosize_table)
            self.w.resizeEvent = handler

        # Hook image preview resize to rescale
        if self.previewImage is not None:
            old_resize = self.previewImage.resizeEvent
            def _on_resize(ev):
                if callable(old_resize):
                    old_resize(ev)
                self._update_preview_scaled()
            self.previewImage.resizeEvent = _on_resize

    def _autosize_table(self):
        if isinstance(self.tableEntries, QTableWidget):
            self.tableEntries.resizeRowsToContents()
            self.tableEntries.resizeColumnsToContents()
            hh: QHeaderView = self.tableEntries.horizontalHeader()
            if hh: hh.setSectionResizeMode(QHeaderView.Stretch)

    def _wire_sig(self, w, sig, fn):
        try:
            if w and hasattr(w, sig): getattr(w, sig).connect(fn)
        except Exception: pass

    def _wire(self):
        self._wire_sig(self.btnAddEntry, "clicked", self.on_add_entry)
        self._wire_sig(self.btnDeleteSelected, "clicked", self.on_delete_selected)
        self._wire_sig(self.btnClearAll, "clicked", self.on_clear_all)
        self._wire_sig(self.btnQuickPdf, "clicked", self.on_quick_pdf)

        self._wire_sig(self.btnMatAddUpdate, "clicked", self.on_mat_add_or_update)
        self._wire_sig(self.btnMatDelete, "clicked", self.on_mat_delete)
        self._wire_sig(self.btnMatEditId, "clicked", self.on_mat_edit_id)
        self._wire_sig(self.listMaterials, "itemDoubleClicked", self.on_mat_edit_id)

        self._wire_sig(self.btnMuniAdd, "clicked", self.on_muni_add)
        self._wire_sig(self.btnMuniDelete, "clicked", self.on_muni_delete)

        self._wire_sig(self.btnUserAdd, "clicked", self.on_user_add)
        self._wire_sig(self.btnUserDelete, "clicked", self.on_user_delete)

        self._wire_sig(self.btnMakeCsv, "clicked", self.on_make_csv)
        self._wire_sig(self.btnMakePdf, "clicked", self.on_make_pdf)
        self._wire_sig(self.btnOpenReport, "clicked", self.on_open_report)
        self._wire_sig(self.btnDeleteReport, "clicked", self.on_delete_report)

        # Image add button
        self._wire_sig(self.btnAddImage, "clicked", self.on_add_image)
        # Update preview on selection changes
        if isinstance(self.listMaterials, QListWidget):
            self.listMaterials.currentItemChanged.connect(lambda *_: self._update_preview_scaled())
            self.listMaterials.itemSelectionChanged.connect(lambda *_: self._update_preview_scaled())

    # ---------- helpers ----------
    def _float_qty(self) -> float:
        if not self.editQty: return 0.0
        try:
            txt=self.editQty.text().strip().replace(",",".")
            return float(txt) if txt else 0.0
        except Exception: return 0.0

    def _valid_date(self, s: str) -> Optional[str]:
        s=s.strip()
        for fmt in ("%Y-%m-%d","%Y/%m/%d","%d-%m-%Y","%d/%m/%Y"):
            try: return datetime.strptime(s, fmt).date().isoformat()
            except ValueError: pass
        return None

    def _date_str(self, le: Optional[QLineEdit]) -> str:
        if isinstance(le, QLineEdit):
            t = le.text().strip()
            if t:
                iso = self._valid_date(t)
                if iso: return iso
        return date.today().isoformat()

    # ---------- consumption ----------
    def on_add_entry(self):
        user = self.comboUser.currentText() if self.comboUser else ""
        muni = self.comboMunicipality.currentText() if self.comboMunicipality else ""
        mid = self.comboMaterial.currentData() if self.comboMaterial else None
        mlabel = self.comboMaterial.currentText() if self.comboMaterial else ""
        qty = self._float_qty()
        d = self._date_str(self.editDate)

        errors=[]
        if not user: errors.append("Välj användare")
        if not muni: errors.append("Välj kommun")
        if not mid: errors.append("Välj material")
        if qty <= 0: errors.append("Ange antal > 0")
        if errors: QMessageBox.warning(self.w,"Ofullständigt","\n".join(errors)); return

        unit = "st"
        for m in self.materials:
            if m.id==mid: unit=m.unit; mlabel=m.label; break

        eid=f"E{int(time.time()*1000)}"
        e = Entry(id=eid,user=user,municipality=muni,materialId=str(mid),materialLabel=mlabel,qty=qty,unit=unit,date=d)
        self.entries.append(e); self.d.save_entries(self.entries)

        if isinstance(self.editQty,QLineEdit): self.editQty.clear()
        self._refresh_entries_table(); self._autosize_table(); self._status("Förbrukning tillagd")

    def _refresh_entries_table(self):
        if not isinstance(self.tableEntries, QTableWidget): return
        headers=["Datum","Användare","Kommun","Material","Antal","Enhet"]
        self.tableEntries.clear()
        self.tableEntries.setColumnCount(len(headers))
        self.tableEntries.setHorizontalHeaderLabels(headers)
        self.tableEntries.setRowCount(len(self.entries))
        for r,e in enumerate(self.entries):
            for c,val in enumerate([e.date,e.user,e.municipality,e.materialLabel,f"{e.qty:g}",e.unit]):
                item=QTableWidgetItem(str(val))
                if c==4: item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
                self.tableEntries.setItem(r,c,item)
        self._autosize_table()

    def _selected_row(self) -> Optional[int]:
        if not isinstance(self.tableEntries, QTableWidget): return None
        r=self.tableEntries.currentRow()
        return r if r>=0 else None

    def on_delete_selected(self):
        idx=self._selected_row()
        if idx is None: return
        if 0<=idx<len(self.entries):
            del self.entries[idx]; self.d.save_entries(self.entries); self._refresh_entries_table(); self._status("Rad borttagen")

    def on_clear_all(self):
        if not self.entries: return
        res=QMessageBox.question(self.w,"Bekräfta","Rensa all förbrukning?")
        if res.name!="Yes": return
        self.entries.clear(); self.d.save_entries(self.entries); self._refresh_entries_table(); self._status("Listan rensad")

    def on_quick_pdf(self):
        if not self.entries:
            QMessageBox.information(self.w,"Ingen data","Inga poster i listan."); return
        rows=[]; by={}
        for e in self.entries: by.setdefault(e.municipality,[]).append(e)
        for muni, es in by.items():
            sums={}
            for e in es: sums[(e.materialLabel,e.unit)]=sums.get((e.materialLabel,e.unit),0.0)+e.qty
            for (label,unit),qty in sums.items(): rows.append((muni, f"- {label}: {qty:g} {unit}", unit))
        out=self.d.create_pdf("Förbrukningsrapport (aktuell lista)", rows)
        self._refresh_reports_list(); self._status(f"PDF skapad: {out.name}")

    # ---------- materials ----------
    def _refresh_materials_list(self):
        if not isinstance(self.listMaterials, QListWidget): return
        self.listMaterials.clear()
        for m in self.materials:
            QListWidgetItem(f"{m.id} — {m.label} ({m.unit})", self.listMaterials)
        if self.listMaterials.count()>0 and self.previewImage is not None:
            self.listMaterials.setCurrentRow(0)
            self._update_preview_scaled()

    def _gen_material_id(self) -> str:
        return "MAT-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    def on_mat_add_or_update(self):
        # PATCH: val mellan spara eller ny, och nollställ förhandsvisning för nya produkter
        current_it = self.listMaterials.currentItem() if self.listMaterials else None
        if current_it is not None:
            box = QMessageBox(self.w)
            box.setWindowTitle("Produkt")
            box.setText("Vill du spara ändringar på vald produkt\neller skapa en ny produkt?")
            btn_save   = box.addButton("Spara ändringar", QMessageBox.AcceptRole)
            btn_new    = box.addButton("Ny produkt", QMessageBox.ActionRole)
            box.addButton(QMessageBox.Cancel)
            box.exec()
            clicked = box.clickedButton()
            if clicked == btn_save:
                unit = self.editMunit.text().strip() if isinstance(self.editMunit,QLineEdit) else ""
                if not unit: unit="st"
                mid = current_it.text().split(" — ",1)[0]
                for m in self.materials:
                    if m.id == mid:
                        m.unit = unit
                        break
                self.d.save_materials(self.materials)
                self._refresh_materials_list(); self._init_ui(); self._status("Enhet uppdaterad")
                return
            elif clicked != btn_new:
                return  # Avbryt

        # Ny produkt-flöde
        name, ok = QInputDialog.getText(self.w, "Ny produkt", "Ange Namn:")
        if not ok or not name.strip(): return
        unit, ok = QInputDialog.getText(self.w, "Ny produkt", "Enhet (t.ex. st, m):", text="st")
        if not ok or not unit.strip(): unit="st"
        mid = self._gen_material_id()
        self.materials.append(Material(id=mid, label=name.strip(), description="", unit=unit.strip()))
        self.d.save_materials(self.materials)
        self._refresh_materials_list(); self._init_ui()
        if self.listMaterials:
            for i in range(self.listMaterials.count()):
                if self.listMaterials.item(i).text().split(" — ",1)[0] == mid:
                    self.listMaterials.setCurrentRow(i); break
        if not self._image_path_for(mid) and self.previewImage:
            self.previewImage.setText("(Ingen bild)"); self.previewImage.setPixmap(QPixmap())
        self._status(f"Ny produkt skapad (ID: {mid})")

    def on_mat_edit_id(self, *args):
        if not isinstance(self.listMaterials, QListWidget): return
        it=self.listMaterials.currentItem()
        if not it: return
        old_mid = it.text().split(" — ",1)[0]
        new_mid, ok = QInputDialog.getText(self.w, "Ändra ID", "Nytt ID:", text=old_mid)
        if not ok or not new_mid.strip(): return
        if new_mid.strip()!=old_mid and any(m.id==new_mid.strip() for m in self.materials):
            QMessageBox.warning(self.w,"Finns redan","Det finns redan en produkt med detta ID."); return
        # Move image file if exists
        self._rename_product_image(old_mid, new_mid.strip())
        for m in self.materials:
            if m.id==old_mid: m.id=new_mid.strip(); break
        self.d.save_materials(self.materials)
        self._refresh_materials_list(); self._init_ui(); self._status("ID uppdaterat")

    def _rename_product_image(self, old_id:str, new_id:str):
        base = product_img_dir()
        for ext in ("png","jpg","jpeg"):
            p = base / f"{old_id}.{ext}"
            if p.exists():
                dst = base / f"{new_id}.{ext}"
                try:
                    if dst.exists(): dst.unlink()
                    p.rename(dst)
                except Exception:
                    pass

    def on_mat_delete(self):
        if not isinstance(self.listMaterials, QListWidget): return
        it=self.listMaterials.currentItem()
        if not it: return
        mid=it.text().split(" — ",1)[0]
        # Remove image files
        for ext in ("png","jpg","jpeg"):
            try: (product_img_dir() / f"{mid}.{ext}").unlink(missing_ok=True)
            except Exception: pass
        self.materials=[m for m in self.materials if m.id!=mid]
        self.d.save_materials(self.materials)
        self._refresh_materials_list(); self._init_ui(); self._status("Produkt borttagen")

    # ---------- municipalities ----------
    def _refresh_muni_list(self):
        if not isinstance(self.listMunis, QListWidget): return
        self.listMunis.clear()
        for n in self.munis: QListWidgetItem(n, self.listMunis)

    def on_muni_add(self):
        name = self.editNewMuni.text().strip() if isinstance(self.editNewMuni,QLineEdit) else ""
        if not name: QMessageBox.information(self.w,"Tomt fält","Ange kommunnamn."); return
        if name in self.munis: QMessageBox.information(self.w,"Finns redan","Kommunen finns redan."); return
        self.munis.append(name); self.d.save_munis(self.munis)
        self._refresh_muni_list(); self._init_ui()
        if isinstance(self.editNewMuni,QLineEdit): self.editNewMuni.clear()
        self._status("Kommun tillagd")

    def on_muni_delete(self):
        if not isinstance(self.listMunis, QListWidget): return
        it=self.listMunis.currentItem()
        if not it: return
        name=it.text()
        self.munis=[x for x in self.munis if x!=name]
        self.d.save_munis(self.munis)
        self._refresh_muni_list(); self._init_ui(); self._status("Kommun borttagen")

    # ---------- users ----------
    def _refresh_user_list(self):
        if not isinstance(self.listUsers, QListWidget): return
        self.listUsers.clear()
        for u in self.users: QListWidgetItem(u, self.listUsers)

    def on_user_add(self):
        name = self.editNewUser.text().strip() if isinstance(self.editNewUser,QLineEdit) else ""
        if not name: QMessageBox.information(self.w,"Tomt fält","Ange användarnamn."); return
        if name in self.users: QMessageBox.information(self.w,"Finns redan","Användaren finns redan."); return
        self.users.append(name); self.d.save_users(self.users)
        self._refresh_user_list(); self._init_ui()
        if isinstance(self.editNewUser,QLineEdit): self.editNewUser.clear()
        self._status("Användare tillagd")

    def on_user_delete(self):
        if not isinstance(self.listUsers, QListWidget): return
        it=self.listUsers.currentItem()
        if not it: return
        name=it.text()
        self.users=[x for x in self.users if x!=name]
        self.d.save_users(self.users)
        self._refresh_user_list(); self._init_ui(); self._status("Användare borttagen")

    # ---------- reports ----------
    def _filtered_entries(self)->List[Entry]:
        from_s = self.editFrom.text().strip() if isinstance(self.editFrom,QLineEdit) else ""
        to_s   = self.editTo.text().strip() if isinstance(self.editTo,QLineEdit) else ""
        uf = self.comboUserF.currentText() if self.comboUserF else "Alla"
        mf = self.comboMuniF.currentText() if self.comboMuniF else "Alla"
        matf = self.comboMatF.currentText() if self.comboMatF else "Alla"

        mat_id=None
        if matf and matf!="Alla":
            for m in self.materials:
                if m.label==matf: mat_id=m.id; break

        out: List[Entry] = []
        for e in self.entries:
            if from_s and e.date < from_s: continue
            if to_s and e.date > to_s: continue
            if uf!="Alla" and e.user!=uf: continue
            if mf!="Alla" and e.municipality!=mf: continue
            if mat_id and e.materialId!=mat_id: continue
            out.append(e)
        return out

    def _refresh_reports_list(self):
        if not isinstance(self.listReports, QListWidget): return
        self.listReports.clear()
        rep_dir = self.d.reports_dir
        rep_dir.mkdir(parents=True, exist_ok=True)
        for fn in sorted(os.listdir(rep_dir)):
            if fn.lower().endswith((".csv",".pdf")):
                QListWidgetItem(fn, self.listReports)

    def on_make_csv(self):
        entries=self._filtered_entries()
        if not entries:
            QMessageBox.information(self.w,"Ingen data","Inga poster matchar filtren."); return
        out=self.d.create_csv(entries)
        self._refresh_reports_list(); self._status(f"CSV skapad: {out.name}")

    def on_make_pdf(self):
        entries=self._filtered_entries()
        if not entries:
            QMessageBox.information(self.w,"Ingen data","Inga poster matchar filtren."); return
        rows=[]; by={}
        for e in entries:
            by.setdefault((e.municipality,e.materialLabel,e.unit),0.0)
            by[(e.municipality,e.materialLabel,e.unit)] += e.qty
        for (muni,label,unit),qty in by.items():
            rows.append((muni, f"- {label}: {qty:g} {unit}", unit))
        out=self.d.create_pdf("Förbrukningsrapport (filter)", rows)
        self._refresh_reports_list(); self._status(f"PDF skapad: {out.name}")

    def on_open_report(self):
        if not isinstance(self.listReports, QListWidget): return
        it=self.listReports.currentItem()
        if not it: return
        path=self.d.reports_dir / it.text()
        try:
            if platform.system()=="Windows":
                os.startfile(str(path))
            elif platform.system()=="Darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            pass

    def on_delete_report(self):
        if not isinstance(self.listReports, QListWidget): return
        it=self.listReports.currentItem()
        if not it: return
        path=self.d.reports_dir / it.text()
        try: path.unlink(missing_ok=True)
        except Exception: pass
        self._refresh_reports_list(); self._status("Rapport borttagen")

    # ---------- images ----------
    def _image_path_for(self, mid:str) -> Optional[Path]:
        base = product_img_dir()
        for ext in ("png","jpg","jpeg"):
            p = base / f"{mid}.{ext}"
            if p.exists(): return p
        return None

    def _update_preview_scaled(self):
        if not self.previewImage: return
        mid=None
        if isinstance(self.listMaterials, QListWidget) and self.listMaterials.currentItem():
            mid = self.listMaterials.currentItem().text().split(" — ",1)[0]
        if not mid:
            self.previewImage.setText("(Ingen bild)"); self.previewImage.setPixmap(QPixmap()); return
        p = self._image_path_for(mid)
        if not p:
            self.previewImage.setText("(Ingen bild)"); self.previewImage.setPixmap(QPixmap()); return
        pm = QPixmap(str(p))
        if pm.isNull():
            self.previewImage.setText("(Fel på bild)"); self.previewImage.setPixmap(QPixmap()); return
        target = self.previewImage.size()
        self.previewImage.setPixmap(pm.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.previewImage.setText("")

    def on_add_image(self):
        if not isinstance(self.listMaterials, QListWidget) or not self.listMaterials.currentItem():
            QMessageBox.information(self.w,"Välj produkt","Markera först en produkt i listan."); return
        mid = self.listMaterials.currentItem().text().split(" — ",1)[0]
        fn, _ = QFileDialog.getOpenFileName(self.w, "Välj bild", "", "Bilder (*.png *.jpg *.jpeg)")
        if not fn: return
        base = product_img_dir()
        ext = os.path.splitext(fn)[1].lower()
        if ext not in (".png",".jpg",".jpeg"): ext = ".png"
        dst = base / f"{mid}{ext}"
        # remove other variants
        for e in ("png","jpg","jpeg"):
            p = base / f"{mid}.{e}"
            if p.exists():
                try: p.unlink()
                except Exception: pass
        try:
            shutil.copyfile(fn, dst)
        except Exception as e:
            QMessageBox.warning(self.w,"Fel vid kopiering", str(e)); return
        self._update_preview_scaled()
        self._status("Bild kopierad till produkt")

    def run(self):
        self.w.show()

# ---------------------------- main ----------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    ic = app_icon()
    if not ic.isNull(): app.setWindowIcon(ic)
    controller = App()
    controller.w.resize(1200, 700)
    controller.w.setMinimumSize(1200, 700)
    controller.run()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
