# Materialappen

En Windows-app byggd med **PySide6**. Läser **UI/QSS/ikoner** från PyInstallers bundle och skriver **data/**, **reports/** och **assets/product_images/** bredvid `.exe`.

## Funktioner
- 📁 **Skrivbara mappar bredvid .exe**: `data/`, `reports/`, `assets/product_images/`
- 📦 **Read-only UI & assets** från bundle (`MEIPASS`): `ui/`, `assets/` (QSS, ikoner)
- 🪟 Förvalt fönster: **1200×700** med samma minsta storlek
- 🧾 Export av rapporter till CSV
- 🖼️ Spara produktbilder via GUI

## Mappstruktur
```
.
├─ assets/                # (bundlas read-only i .exe)
│  ├─ icons/
│  │  └─ icon.ico|png
│  └─ qss/
│     └─ win11.qss
├─ data/                  # (skapas vid körning bredvid .exe)
├─ reports/               # (skapas vid körning bredvid .exe)
├─ ui/                    # (bundlas read-only i .exe)
├─ materialappen_v7_win11_full_images_fix_patched2.py
├─ Materialappen.spec
└─ requirements.txt
```

> I fryst läge hämtas **UI/QSS/ikoner** från `sys._MEIPASS`. I utvecklingsläge används filer från projektmappen.

## Komma igång (utveckling)
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python materialappen_v7_win11_full_images_fix_patched2.py
```

## Bygga .exe (PyInstaller / Windows CMD)
```bat
py -m pip install --upgrade pip
py -m pip install pyinstaller -r requirements.txt

py -m PyInstaller --noconsole --onefile ^
  --name Materialappen ^
  --icon assets\icons\icon.ico ^
  --add-data "ui;ui" ^
  --add-data "assets;assets" ^
  materialappen_v7_win11_full_images_fix_patched2.py
```
- `dist\Materialappen.exe` är din körbara fil.
- Vid första start skapas `data\` och `reports\` bredvid `.exe`.
- Produktbilder sparas i `assets\product_images\` bredvid `.exe`.

## Krav
- Python 3.9+ (testat med 3.13)
- Se `requirements.txt`

## Licens
Se [LICENSE](LICENSE). Standard är MIT – byt gärna till det som passar dig.

## Bidra
Se [CONTRIBUTING.md](CONTRIBUTING.md) och [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Felsökning
- **'pyinstaller' is not recognized…** → installera: `py -m pip install pyinstaller`
- **Ikon laddas inte** → stämmer sökvägen `assets/icons/icon.ico`? Prova köra utan `--icon`.
- **UI/QSS saknas** → ser du `--add-data "ui;ui"` och `"assets;assets"` i kommandot?

---

> Tips: Döp gärna huvudfilen till `main.py` och lägg den i en `src/`-mapp om du vill ha en ännu renare repo-struktur.
