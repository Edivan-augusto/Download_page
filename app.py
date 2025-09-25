#!/usr/bin/env python3
import os, pathlib, time, hashlib, zipfile
from flask import Flask, render_template, send_from_directory, request, abort, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

APP_DIR = pathlib.Path(__file__).resolve().parent
FILES_DIR = APP_DIR / 'files'
FILES_DIR.mkdir(exist_ok=True)

# --- Config via env vars ---
UPLOAD_TOKEN = os.getenv('UPLOAD_TOKEN', '')  # if set, required for /upload
INDEX_TOKEN  = os.getenv('INDEX_TOKEN', '')   # if set, required to view / (pass as ?t=TOKEN or header X-Index-Token)
BLOCK_EMPTY_ZIP = os.getenv('BLOCK_EMPTY_ZIP', '0') in ('1', 'true', 'True')
MAX_CONTENT_LENGTH_MB = int(os.getenv('MAX_CONTENT_LENGTH_MB', '200'))  # default 200MB
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH_MB * 1024 * 1024
app.secret_key = SECRET_KEY

# --- Helpers ---
def _fmt_size(num: int) -> str:
    for unit in ['B','KB','MB','GB','TB']:
        if num < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"

def _list_files():
    out = []
    for p in sorted(FILES_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file():
            continue
        st = p.stat()
        entry = {
            'name': p.name,
            'size': st.st_size,
            'size_h': _fmt_size(st.st_size),
            'mtime': int(st.st_mtime),
            'mtime_iso': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime)),
            'sha12': hashlib.sha256(p.read_bytes()).hexdigest()[:12],
            'zip': None
        }
        if p.suffix.lower() == '.zip':
            try:
                with zipfile.ZipFile(p, 'r') as z:
                    entry['zip'] = {
                        'count': len(z.infolist()),
                        'empty': len(z.infolist()) == 0,
                        'bad': False
                    }
            except zipfile.BadZipFile:
                entry['zip'] = {'count': 0, 'empty': True, 'bad': True}
        out.append(entry)
    return out

def _check_index_auth(req) -> bool:
    if not INDEX_TOKEN:
        return True
    return req.args.get('t') == INDEX_TOKEN or req.headers.get('X-Index-Token') == INDEX_TOKEN

def _check_upload_auth(req) -> bool:
    if not UPLOAD_TOKEN:
        return True
    tok = req.args.get('token') or req.form.get('token') or req.headers.get('X-Upload-Token')
    return tok == UPLOAD_TOKEN

# --- Routes ---
@app.get('/')
def index():
    if not _check_index_auth(request):
        return abort(401, description='Missing or invalid INDEX_TOKEN')
    files = _list_files()
    return render_template('index.html', files=files, has_upload=bool(UPLOAD_TOKEN))

@app.get('/api/list')
def api_list():
    if not _check_index_auth(request):
        return abort(401, description='Missing or invalid INDEX_TOKEN')
    return jsonify(_list_files())

@app.get('/dl/<path:filename>')
def download(filename):
    # sanitize and check existence
    safe = pathlib.Path(secure_filename(filename))
    target = (FILES_DIR / safe.name)
    if not target.exists() or not target.is_file():
        abort(404)
    # enforce optional zip policy
    if target.suffix.lower() == '.zip' and BLOCK_EMPTY_ZIP:
        try:
            with zipfile.ZipFile(target, 'r') as z:
                if len(z.infolist()) == 0:
                    abort(409, description='ZIP vazio bloqueado pelo servidor (BLOCK_EMPTY_ZIP=1)')
        except zipfile.BadZipFile:
            abort(409, description='ZIP corrompido bloqueado pelo servidor (BLOCK_EMPTY_ZIP=1)')
    # stream download
    resp = send_from_directory(FILES_DIR, target.name, as_attachment=True)
    # avoid stale caching for frequently replaced artifacts
    resp.headers['Cache-Control'] = 'no-store, max-age=0'
    return resp

@app.get('/upload')
def upload_form():
    if not _check_upload_auth(request):
        return abort(401, description='Missing or invalid UPLOAD_TOKEN')
    return render_template('upload.html')

@app.post('/upload')
def upload_post():
    if not _check_upload_auth(request):
        return abort(401, description='Missing or invalid UPLOAD_TOKEN')
    if 'file' not in request.files:
        flash('Nenhum arquivo enviado', 'error')
        return redirect(url_for('upload_form'))
    f = request.files['file']
    if f.filename == '':
        flash('Arquivo sem nome', 'error')
        return redirect(url_for('upload_form'))
    name = secure_filename(f.filename)
    dest = FILES_DIR / name
    f.save(dest)
    # Optionally reject empty zips right after upload
    if dest.suffix.lower() == '.zip' and BLOCK_EMPTY_ZIP:
        try:
            with zipfile.ZipFile(dest, 'r') as z:
                if len(z.infolist()) == 0:
                    dest.unlink(missing_ok=True)
                    flash('ZIP vazio rejeitado (server BLOCK_EMPTY_ZIP=1)', 'error')
                    return redirect(url_for('upload_form'))
        except zipfile.BadZipFile:
            dest.unlink(missing_ok=True)
            flash('ZIP corrompido rejeitado (server BLOCK_EMPTY_ZIP=1)', 'error')
            return redirect(url_for('upload_form'))
    flash(f'Upload OK: {name}', 'ok')
    return redirect(url_for('index'))

@app.get('/healthz')
def health():
    return {'ok': True}

if __name__ == '__main__':
    port = int(os.getenv('PORT', '8080'))
    app.run(host='0.0.0.0', port=port, debug=False)
