import os, re, sqlite3, uuid
from pathlib import Path
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort, send_from_directory)
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
DB = ROOT / "database.db"
UPLOADS = ROOT / "uploads"
MUSIC_DIR = ROOT / "static" / "music"
UPLOADS.mkdir(exist_ok=True)
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.template_folder = 'templates' 
app.secret_key = os.environ.get("SECRET_KEY", "replace-this-with-a-long-random-secret")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}
AUDIO_EXT = {"mp3", "ogg", "wav", "m4a"}

THEMES = {
    "royal-gold":    "Royal Gold",
    "pink-floral":   "Pink Floral",
    "traditional":   "Traditional Indian",
    "green-garden":  "Green Garden",
    "modern-luxury": "Modern Luxury",
}

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS invitations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL,
            bride TEXT NOT NULL, groom TEXT NOT NULL, wedding_date TEXT, venue TEXT,
            address TEXT, message TEXT, bride_family TEXT, groom_family TEXT,
            events TEXT, photo TEXT, music TEXT, theme TEXT DEFAULT 'royal-gold',
            map_link TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        con.execute("""CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT, invitation_id INTEGER NOT NULL,
            guest_name TEXT NOT NULL, response TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(invitation_id) REFERENCES invitations(id))""")
        con.execute("""CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, invitation_id INTEGER NOT NULL,
            filename TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(invitation_id) REFERENCES invitations(id))""")
        for col, ddl in [
            ("music", "ALTER TABLE invitations ADD COLUMN music TEXT"),
            ("theme", "ALTER TABLE invitations ADD COLUMN theme TEXT DEFAULT 'royal-gold'"),
            ("map_link", "ALTER TABLE invitations ADD COLUMN map_link TEXT")]:
            try: con.execute(ddl)
            except sqlite3.OperationalError: pass

def admin_only(fn):
    @wraps(fn)
    def wrapped(*a, **k):
        if not session.get("admin"): return redirect(url_for("login"))
        return fn(*a, **k)
    return wrapped

def valid_slug(v):
    v = (v or "").lower().strip()
    v = re.sub(r"[^a-z0-9-]+", "-", v)
    return re.sub(r"-+", "-", v).strip("-")[:60]

def get_invite(slug):
    with db() as con:
        return con.execute("SELECT * FROM invitations WHERE slug=?", (slug,)).fetchone()

def get_photos(invite_id):
    with db() as con:
        return con.execute("SELECT * FROM photos WHERE invitation_id=? ORDER BY id", (invite_id,)).fetchall()

def save_upload(file, allowed, folder):
    if not file or not file.filename: return ""
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed: raise ValueError(f"Unsupported file type .{ext}")
    name = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    file.save(folder / name)
    return name

@app.route("/")
def home():
    if session.get("admin"): return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = os.environ.get("ADMIN_USERNAME", "admin")
        p = os.environ.get("ADMIN_PASSWORD", "change-me-now")
        if request.form.get("username") == u and request.form.get("password") == p:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        flash("Username or password is incorrect.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@admin_only
def dashboard():
    with db() as con:
        invites = con.execute("SELECT * FROM invitations ORDER BY id DESC").fetchall()
    return render_template("dashboard.html", invites=invites)

@app.route("/admin/new", methods=["GET", "POST"])
@admin_only
def new_invitation():
    if request.method == "POST":
        bride = request.form.get("bride", "").strip()
        groom = request.form.get("groom", "").strip()
        slug = valid_slug(request.form.get("slug", "") or f"{bride}-weds-{groom}")
        if not bride or not groom or not slug:
            flash("Bride, groom and link name are required.")
            return render_template("edit.html", invite=None, themes=THEMES)
        try:
            photo = save_upload(request.files.get("photo"), IMAGE_EXT, UPLOADS)
            music = save_upload(request.files.get("music"), AUDIO_EXT, MUSIC_DIR)
        except ValueError as e:
            flash(str(e))
            return render_template("edit.html", invite=None, themes=THEMES)
        values = (slug, bride, groom, request.form.get("wedding_date", ""),
            request.form.get("venue", ""), request.form.get("address", ""),
            request.form.get("message", "With love, we invite you to celebrate our special day."),
            request.form.get("bride_family", ""), request.form.get("groom_family", ""),
            request.form.get("events", ""), photo, music,
            request.form.get("theme", "royal-gold"), request.form.get("map_link", ""))
        try:
            with db() as con:
                cur = con.execute("""INSERT INTO invitations
                (slug,bride,groom,wedding_date,venue,address,message,
                 bride_family,groom_family,events,photo,music,theme,map_link)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", values)
                invite_id = cur.lastrowid
            flash("Invitation created.")
            return redirect(url_for("edit_invitation", invite_id=invite_id))
        except sqlite3.IntegrityError:
            flash("That link name already exists.")
    return render_template("edit.html", invite=None, themes=THEMES)

@app.route("/admin/edit/<int:invite_id>", methods=["GET", "POST"])
@admin_only
def edit_invitation(invite_id):
    with db() as con:
        invite = con.execute("SELECT * FROM invitations WHERE id=?", (invite_id,)).fetchone()
    if not invite: abort(404)
    if request.method == "POST":
        bride = request.form.get("bride", "").strip()
        groom = request.form.get("groom", "").strip()
        slug = valid_slug(request.form.get("slug", ""))
        if not bride or not groom or not slug:
            flash("Bride, groom and link name are required.")
            return redirect(url_for("edit_invitation", invite_id=invite_id))
        photo, music = invite["photo"], invite["music"]
        try:
            if request.files.get("photo") and request.files["photo"].filename:
                photo = save_upload(request.files["photo"], IMAGE_EXT, UPLOADS)
            if request.files.get("music") and request.files["music"].filename:
                music = save_upload(request.files["music"], AUDIO_EXT, MUSIC_DIR)
            for f in request.files.getlist("gallery"):
                if f and f.filename:
                    fn = save_upload(f, IMAGE_EXT, UPLOADS)
                    with db() as con:
                        con.execute("INSERT INTO photos (invitation_id,filename) VALUES (?,?)", (invite_id, fn))
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("edit_invitation", invite_id=invite_id))
        try:
            with db() as con:
                con.execute("""UPDATE invitations SET slug=?,bride=?,groom=?,wedding_date=?,
                venue=?,address=?,message=?,bride_family=?,groom_family=?,events=?,
                photo=?,music=?,theme=?,map_link=? WHERE id=?""",
                (slug, bride, groom, request.form.get("wedding_date", ""),
                 request.form.get("venue", ""), request.form.get("address", ""),
                 request.form.get("message", ""), request.form.get("bride_family", ""),
                 request.form.get("groom_family", ""), request.form.get("events", ""),
                 photo, music, request.form.get("theme", "royal-gold"),
                 request.form.get("map_link", ""), invite_id))
        except sqlite3.IntegrityError:
            flash("Link name already used by another invitation.")
            return redirect(url_for("edit_invitation", invite_id=invite_id))
        flash("Invitation updated.")
        return redirect(url_for("edit_invitation", invite_id=invite_id))
    with db() as con:
        invite = con.execute("SELECT * FROM invitations WHERE id=?", (invite_id,)).fetchone()
    public_link = request.url_root.rstrip("/") + url_for("public_invitation", slug=invite["slug"])
    return render_template("edit.html", invite=invite, public_link=public_link,
                           themes=THEMES, photos=get_photos(invite_id))

@app.route("/admin/photo/<int:photo_id>/delete", methods=["POST"])
@admin_only
def delete_photo(photo_id):
    with db() as con:
        row = con.execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()
        if row:
            con.execute("DELETE FROM photos WHERE id=?", (photo_id,))
            try: (UPLOADS / row["filename"]).unlink()
            except OSError: pass
            flash("Photo removed.")
            return redirect(url_for("edit_invitation", invite_id=row["invitation_id"]))
    abort(404)

@app.route("/admin/delete/<int:invite_id>", methods=["POST"])
@admin_only
def delete_invitation(invite_id):
    with db() as con:
        con.execute("DELETE FROM rsvps WHERE invitation_id=?", (invite_id,))
        con.execute("DELETE FROM photos WHERE invitation_id=?", (invite_id,))
        con.execute("DELETE FROM invitations WHERE id=?", (invite_id,))
    flash("Invitation deleted.")
    return redirect(url_for("dashboard"))

@app.route("/invite/<slug>")
def public_invitation(slug):
    inv = get_invite(slug)
    if not inv: abort(404)
    return render_template("invitation.html", invite=inv, photos=get_photos(inv["id"]), themes=THEMES)

@app.route("/invite/<slug>/rsvp", methods=["POST"])
def rsvp(slug):
    inv = get_invite(slug)
    if not inv: abort(404)
    guest = request.form.get("guest_name", "").strip()
    resp = request.form.get("response", "")
    if not guest or resp not in {"Attending", "Not attending"}:
        flash("Please enter your name and select a response.")
    else:
        with db() as con:
            con.execute("INSERT INTO rsvps (invitation_id,guest_name,response) VALUES (?,?,?)",
                        (inv["id"], guest, resp))
        flash("Thank you! Your RSVP has been saved.")
    return redirect(url_for("public_invitation", slug=slug) + "#rsvp")

@app.route("/admin/rsvps/<int:invite_id>")
@admin_only
def view_rsvps(invite_id):
    with db() as con:
        inv = con.execute("SELECT * FROM invitations WHERE id=?", (invite_id,)).fetchone()
        if not inv: abort(404)
        guests = con.execute("SELECT * FROM rsvps WHERE invitation_id=? ORDER BY id DESC", (invite_id,)).fetchall()
    return render_template("rsvps.html", invite=inv, guests=guests)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOADS, filename)

@app.errorhandler(413)
def too_large(_):
    return "File too large. Max upload size is 25 MB.", 413

init_db()
if __name__ == "__main__":
    app.run(debug=True)
