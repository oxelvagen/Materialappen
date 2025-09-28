# Materialappen — MEIPASS-ready build (read from bundle, write next to .exe)
# Works both as .py and as PyInstaller onefile .exe
from pathlib import Path
import sys, json, csv
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStatusBar, QLabel, QFileDialog, QMessageBox, QPushButton, QVBoxLayout
)

APP_NAME = "Materialappen"
DATA_DIR = "data"
REPORTS_DIR = "reports"
PRODUCT_IMG_DIR = "assets/product_images"
APP_ICON = "icon.png"
QSS_PATH = "assets/qss/win11.qss"

def is_frozen() -> bool:
    return getattr(sys, "frozen", False)

def bundle_dir() -> Path:
    # Where we READ bundled resources when frozen
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent

def run_dir() -> Path:
    # Where we WRITE runtime data (next to the .exe when frozen, or next to this .py)
    return (Path(sys.executable).resolve().parent if is_frozen()
            else Path(__file__).resolve().parent)

def assets_path() -> Path:
    return bundle_dir() / "assets"

def icon_path() -> Path:
    return assets_path() / "icons" / APP_ICON

def product_img_dir() -> Path:
    p = run_dir() / PRODUCT_IMG_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p

@dataclass
class Entry:
    id: str
    user: str
    municipality: str
    material_id: str
    qty: float
    unit: str
    created_at: str

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

class Data:
    def __init__(self, base: Optional[Path] = None):
        base = base or run_dir()
        self.data_dir = base / DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir = base / REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.p_entries = self.data_dir / "entries.json"
        self.p_materials = self.data_dir / "materials.json"
        self.p_users = self.data_dir / "users.json"
        self.p_munis = self.data_dir / "municipalities.json"
        # Init defaults if missing
        if not self.p_entries.exists(): self.p_entries.write_text("[]", encoding="utf-8")
        if not self.p_materials.exists(): self.p_materials.write_text(json.dumps([
            {"id":"7778234","label":"Fundament 108/900","description":"FUNDAMENT MEAG 108/900","unit":"st","favorite":True},
            {"id":"7779866","label":"Stolpinsats (komplett)","description":"Stolpinsats","unit":"st","favorite":True},
            {"id":"cw25-k1","label":"Armatur CW-25 (klass1, jordad)","description":"","unit":"st","favorite":False},
        ], ensure_ascii=False, indent=2), encoding="utf-8")
        if not self.p_users.exists(): self.p_users.write_text(json.dumps(["Andreas","Kollega"], ensure_ascii=False, indent=2), encoding="utf-8")
        if not self.p_munis.exists(): self.p_munis.write_text(json.dumps(["Nora","Lindesberg","Hällefors","Ljusnarsberg"], ensure_ascii=False, indent=2), encoding="utf-8")

    # Basic IO
    def load_entries(self) -> List[Dict[str, Any]]:
        return json.loads(self.p_entries.read_text(encoding="utf-8"))

    def save_entries(self, entries: List[Dict[str, Any]]) -> None:
        self.p_entries.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    def export_csv(self, filename: Optional[Path] = None) -> Path:
        out = filename or (self.reports_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        entries = self.load_entries()
        cols = ["id","user","municipality","material_id","qty","unit","created_at"]
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for e in entries:
                w.writerow({k: e.get(k,"") for k in cols})
        return out

def apply_qss(app: QApplication) -> None:
    qss = bundle_dir() / QSS_PATH
    if qss.is_file():
        app.setStyleSheet(qss.read_text(encoding="utf-8"))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 700)
        self.setMinimumSize(QSize(1200, 700))
        # Icon from bundle
        ic = icon_path()
        if ic.is_file():
            self.setWindowIcon(QIcon(str(ic)))
        # Data handle uses run_dir()
        self.data = Data(run_dir())

        # Simple content
        central = QWidget(self)
        lay = QVBoxLayout(central)
        self.info = QLabel("", self)
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.info)

        btn_add = QPushButton("Lägg till exempelpost", self)
        btn_add.clicked.connect(self.add_sample)
        lay.addWidget(btn_add)

        btn_img = QPushButton("Spara produktbild…", self)
        btn_img.clicked.connect(self.save_product_image)
        lay.addWidget(btn_img)

        btn_csv = QPushButton("Exportera rapport (CSV) till reports/", self)
        btn_csv.clicked.connect(self.export_csv)
        lay.addWidget(btn_csv)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar(self))
        self.refresh_info()

    def refresh_info(self):
        info = [
            f"Run dir (skrivbar): {run_dir()}",
            f"Bundle dir (read-only): {bundle_dir()}",
            f"Data-dir: {self.data.data_dir}",
            f"Reports-dir: {self.data.reports_dir}",
            f"Produktbilder (skrivbar): {product_img_dir()}",
            f"QSS (bundle): {bundle_dir()/QSS_PATH}",
            f"Ikon (bundle): {icon_path()}",
        ]
        self.info.setText("\n".join(info))

    def add_sample(self):
        entries = self.data.load_entries()
        entries.append(Entry(
            id=str(len(entries)+1),
            user="Andreas",
            municipality="Nora",
            material_id="7778234",
            qty=1,
            unit="st",
            created_at=datetime.now().isoformat(timespec="seconds")
        ).to_json())
        self.data.save_entries(entries)
        self.statusBar().showMessage("En post lades till i data/entries.json", 3000)
        self.refresh_info()

    def save_product_image(self):
        # Pick any image, then copy to writeable product_img_dir
        src, _ = QFileDialog.getOpenFileName(self, "Välj bild", str(run_dir()), "Bilder (*.png *.jpg *.jpeg *.bmp)")
        if not src:
            return
        dst_dir = product_img_dir()
        name = Path(src).name
        dst = dst_dir / name
        try:
            pm = QPixmap(src)
            if pm.isNull():
                raise RuntimeError("Kunde inte läsa bild.")
            pm.save(str(dst))
            QMessageBox.information(self, APP_NAME, f"Sparade produktbild: {dst}")
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, f"Kunde inte spara bild:\n{e}")

    def export_csv(self):
        out = self.data.export_csv()
        QMessageBox.information(self, APP_NAME, f"Exporterade rapport:\n{out}")

def main():
    app = QApplication(sys.argv)
    apply_qss(app)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
