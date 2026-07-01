# RustWatch — Steel Bridge Corrosion Detection (Web App)

A Flask website that detects **rust/corrosion severity** on steel bridge components
using a YOLOv8 model, stores each inspection in a MySQL database, and shows the
results on a dashboard. It also connects to a **Raspberry Pi 5** field camera that
can upload its own captures and stream a live view.

> **New here? Read this whole file once, top to bottom.** It assumes you have never
> run a Python or database project before. Every step tells you *what* to do and
> *why*.

---

## 1. What this app does (in plain words)

- You **upload a photo** of a steel bridge part → the app runs an AI model → it draws
  boxes on the rust and gives a **severity rating** (Good / Fair / Poor / Bad).
- You can **save** that result as an "inspection" record.
- The **Dashboard** shows totals and recent inspections.
- The **Inspections** page lists every saved record; each one has a detail page.
- A **Raspberry Pi 5** with a camera can (a) send its own captures straight into the
  app, and (b) show a **live camera view** on the New Inspection page.

---

## 2. What you need before starting

Install these first (all free):

| Tool | Why | Where |
|------|-----|-------|
| **Python 3.10+** | Runs the app | https://www.python.org/downloads/ (tick *"Add Python to PATH"* during install) |
| **XAMPP** (or any MySQL) | The database that stores inspections | https://www.apachefriends.org/ |
| **Git** *(optional)* | To download/update the code | https://git-scm.com/ |
| A web browser | To view the site | You already have one |

You also need the **AI model file**: `models/best.pt`. If it isn't in the `models/`
folder, ask whoever shared the project for it — the app runs without it but **cannot
detect anything**.

---

## 3. Project layout (what the files are)

```
bridge-detection-web/
├── app.py                 # The web server — start the app by running this
├── database.py            # Talks to MySQL (save/read inspections)
├── config.py              # ⚙️ SETTINGS YOU EDIT (database + Pi camera)
├── severity.py            # Turns detections into a severity rating
├── requirements.txt       # The Python packages to install
├── setup_database.sql     # Creates the database tables
├── migrate_*.sql          # One-time database updates (run after setup)
├── models/best.pt         # The trained AI model (not always included)
├── templates/             # The web pages (HTML)
│   ├── index.html         #   New Inspection page (upload + live camera)
│   ├── dashboard.html
│   ├── inspections_list.html
│   ├── inspection_detail.html
│   └── inspection_edit.html
└── static/
    ├── css/style.css
    ├── uploads/           # Uploaded images (created at runtime)
    └── results/           # Images with detection boxes (created at runtime)
```

---

## 4. Setup — do this once

### Step 1 — Get the code
If you have Git:
```bash
git clone https://github.com/CML03012005/bridge-detection-web.git
cd bridge-detection-web
```
Otherwise download the ZIP from GitHub and unzip it, then open a terminal **inside**
the `bridge-detection-web` folder.

### Step 2 — Create a virtual environment (keeps packages tidy)
```bash
python -m venv venv
```
Activate it (**do this every time you open a new terminal**):
- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`
- **Windows (CMD):** `venv\Scripts\activate.bat`
- **macOS / Linux:** `source venv/bin/activate`

You'll know it worked when the prompt starts with `(venv)`.

### Step 3 — Install the Python packages
```bash
pip install -r requirements.txt
```
> This downloads a lot (the AI library `ultralytics` includes PyTorch). It can take
> several minutes the first time. That's normal.

### Step 4 — Start MySQL and create the database
1. Open the **XAMPP Control Panel** → click **Start** next to **MySQL**.
2. Click **Admin** next to MySQL (opens **phpMyAdmin** in your browser).
3. Create a new database named exactly **`bridge_inspection`**
   (left sidebar → *New* → type the name → *Create*).
4. Select that database → open the **SQL** tab → paste the contents of
   [`setup_database.sql`](setup_database.sql) → **Go**. This creates the tables.
5. Do the same for the two migration files (run each once):
   [`migrate_severity_to_low_med_high.sql`](migrate_severity_to_low_med_high.sql)
   then [`migrate_drop_coverage_patches.sql`](migrate_drop_coverage_patches.sql).

### Step 5 — Point the app at your database
Open [`config.py`](config.py) and check `DB_CONFIG`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3307,          # ⚠️ Most MySQL/XAMPP installs use 3306, not 3307!
    'user': 'root',
    'password': '',        # XAMPP default is empty; set yours if you have one
    'database': 'bridge_inspection',
    ...
}
```
> **The single most common mistake:** the `port`. Open phpMyAdmin → the MySQL port is
> shown there (usually **3306**). Make `config.py` match it, or you'll get a
> "cannot connect to MySQL" error on the Inspections page.

### Step 6 — Make sure the model is present
Confirm the file `models/best.pt` exists. If it's missing, detection won't work
(the app will still start and print a warning).

---

## 5. Run the app

With the virtual environment active and MySQL running:
```bash
python app.py
```
You should see:
```
✅ Rust detection model loaded
✅ Database connected successfully
```
Then open your browser to **http://127.0.0.1:5000**.

To stop the app, press **Ctrl + C** in the terminal.

---

## 6. How to use the website

- **New Inspection** (home): two ways to get an image —
  - **Upload Image** (left card): drag a photo in or click to browse. The page then
    shows a **review**: the image with rust boxes, a results panel (severity,
    detected regions, confidence), and **Save Inspection / Discard** buttons.
  - **Live Camera** (right card): shows the Raspberry Pi's live camera (see §7).
- **Dashboard**: totals and recent inspections.
- **Inspections**: every saved record, with **All / RPi5 Field Scans / Web Uploads**
  filters. Click one to view, edit, or delete it.

---

## 7. Raspberry Pi 5 camera (optional)

The Pi runs a separate program (`detect_lcd.py`, in the **rust-severity-detection**
repo) that detects rust on a live camera and can talk to this website in two ways:

1. **Uploads (Pi → website):** when the Pi saves a capture, it POSTs it to this app's
   `/upload-rpi5` endpoint. Those show up under **Inspections → RPi5 Field Scans**.
   - The Pi must know **this laptop's IP** (it's set on the Pi side, not here).
2. **Live view (website → Pi):** the *Live Camera* card embeds the Pi's video stream.
   - Set the Pi's address here in [`config.py`](config.py):
     ```python
     PI_STREAM_URL = 'http://<PI-IP>:8000/video_feed'
     ```
   - Leave it blank (`''`) to hide the Live Camera card.

**Both devices must be able to reach each other over the network.** On the same
Wi-Fi, use each device's local IP. If you move between networks, install
**Tailscale** on both the laptop and the Pi — it gives each a fixed address that
works anywhere, so you never edit IPs again.

> ⚠️ **Windows Firewall** often blocks incoming connections to the app on port 5000,
> which makes Pi uploads fail. Allow it once (PowerShell **as Administrator**):
> ```powershell
> New-NetFirewallRule -DisplayName "RustWatch Flask 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
> ```

---

## 8. Troubleshooting

| Symptom | Likely cause & fix |
|---------|--------------------|
| **"Error loading inspections" / cannot connect to MySQL** | MySQL isn't running, or `config.py` `port`/`password` is wrong. Start MySQL in XAMPP; make the `port` match phpMyAdmin (usually **3306**). |
| **Page loads but detection does nothing** | `models/best.pt` is missing. Add the model file, restart. |
| **`ModuleNotFoundError` when running** | Virtual environment not active, or packages not installed. Activate `venv`, run `pip install -r requirements.txt`. |
| **`python` not found** | Python isn't on PATH. Reinstall Python and tick *"Add to PATH"*, or use `py` instead of `python` on Windows. |
| **Live Camera says "Can't reach the camera"** | The Pi program isn't running, `PI_STREAM_URL` is wrong, or the two devices can't reach each other. Check the Pi is on and on the same network (or Tailscale). |
| **Pi uploads never appear** | Firewall on port 5000 (see §7), or the Pi is pointed at the wrong laptop IP. |
| **Port 5000 already in use** | Another app is using it. Stop that app, or change the port at the bottom of `app.py`. |

---

## 9. Everyday commands (cheat sheet)

```bash
# every new terminal: go to the folder and activate the environment
cd bridge-detection-web
venv\Scripts\Activate.ps1        # Windows PowerShell

# start the app
python app.py                    # then open http://127.0.0.1:5000

# stop the app
Ctrl + C

# update to the latest code (if you used Git)
git pull
```

Always make sure **MySQL is running** (XAMPP) before starting the app.

---

## 10. Good to know

- **Nothing is public.** The site and database run **on your machine** (`localhost`).
  Another person running the code has their *own* empty database — data isn't shared
  unless you deliberately host it.
- Uploaded and result images live in `static/uploads/` and `static/results/`. These
  are **not** tracked by Git (they're your data), so they won't be in a fresh clone.
- The app currently runs in Flask's **development server** — fine for demos and local
  use, not meant for public production hosting.
