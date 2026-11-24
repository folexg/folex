import os, re, tempfile, shutil
from flask import Flask, request, jsonify, send_file, send_from_directory, after_this_request, redirect
import yt_dlp

app = Flask(__name__, static_folder="static")
URL_RE = re.compile(r"^https?://", re.I)
VIDEO_FMT = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"

def clean(url):
    url = (url or "").strip()
    return url if URL_RE.match(url) else None

def est(f, dur):
    s = f.get("filesize") or f.get("filesize_approx")
    if s:
        return int(s)
    tbr = f.get("tbr") or ((f.get("vbr") or 0) + (f.get("abr") or 0))
    return int(tbr * 125 * dur) if tbr and dur else 0

def sizes(d):
    dur = d.get("duration") or 0
    parts = [est(f, dur) for f in (d.get("requested_formats") or [d])]
    video = sum(parts) if parts and all(parts) else 0
    audio = int(dur * 16250) if dur else 0
    return video or None, audio or None

def probe(url):
    base = {"quiet": True, "skip_download": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL({**base, "format": VIDEO_FMT}) as y:
            return y.extract_info(url, download=False)
    except Exception:
        with yt_dlp.YoutubeDL(base) as y:
            return y.extract_info(url, download=False)

def page(name, **kw):
    return send_from_directory("static", name, **kw)

@app.after_request
def headers(r):
    r.headers.setdefault("Cache-Control", "no-cache")
    r.headers["X-Content-Type-Options"] = "nosniff"
    return r

@app.get("/")
def home():
    return page("index.html")

@app.get("/privacy")
def privacy():
    return page("privacy.html")

@app.get("/terms")
def terms():
    return page("terms.html")

@app.get("/manifest.json")
def manifest():
    return page("manifest.json", mimetype="application/manifest+json")

@app.get("/sw.js")
def sw():
    r = page("sw.js", mimetype="text/javascript")
    r.headers["Service-Worker-Allowed"] = "/"
    return r

@app.get("/favicon.ico")
def favicon():
    return page("favicon.ico")

@app.post("/share-target")
def share_fallback():
    return redirect("/", code=303)

@app.get("/api/info")
def info():
    url = clean(request.args.get("url"))
    if not url:
        return jsonify(error="Paste a full link starting with https://"), 400
    try:
        d = probe(url)
        vsize, asize = sizes(d)
        return jsonify(title=d.get("title") or "Video", thumb=d.get("thumbnail"),
                       duration=d.get("duration"), site=d.get("extractor_key"),
                       vsize=vsize, asize=asize)
    except Exception:
        return jsonify(error="Could not read that link. It may be private, removed or not supported."), 422

@app.get("/api/download")
def download():
    url = clean(request.args.get("url"))
    audio = request.args.get("audio") == "1"
    tok = re.sub(r"[^A-Za-z0-9]", "", request.args.get("t", ""))[:40]
    if not url:
        return "Bad link", 400
    tmp = tempfile.mkdtemp()
    opts = {"quiet": True, "noplaylist": True, "outtmpl": os.path.join(tmp, "%(title).80s.%(ext)s"),
            "format": "bestaudio/best" if audio else VIDEO_FMT,
            "merge_output_format": "mp4"}
    if audio:
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.extract_info(url, download=True)
        f = os.path.join(tmp, os.listdir(tmp)[0])
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        return "Download failed", 422

    @after_this_request
    def _c(r):
        shutil.rmtree(tmp, ignore_errors=True)
        return r

    resp = send_file(f, as_attachment=True)
    resp.headers["Cache-Control"] = "no-store"
    if tok:
        resp.set_cookie("dlstart", tok, max_age=120, path="/", samesite="Lax")
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
