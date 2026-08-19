import http.server
import socketserver
import json
import webbrowser
import urllib.parse
import sys
from deobfuscate import deobfuscatechaoticgood

htmlpage = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LuaObfuscator ChaoticGood Deobfuscator</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
<style id="themestyle">
:root {
  --bg-body: #1a1a1a;
  --bg-card: #2d2d2d;
  --border-card: #444;
  --text-primary: #e0e0e0;
  --text-secondary: #aaa;
  --header-bg: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
  --header-text: #1a1a1a;
  --header-shadow: 0 8px 32px rgba(0,0,0,0.5);
  --input-bg: #1e1e1e;
  --input-text: #e0e0e0;
  --input-border: #444;
  --input-placeholder: #888;
  --btn-bg: #f7971e;
  --btn-hover: #d6851a;
  --btn-text: #1a1a1a;
  --upload-border: #666;
  --upload-hover: #f7971e;
  --upload-bg: #2d2d2d;
  --upload-text: #e0e0e0;
  --shadow: 0 4px 20px rgba(0,0,0,0.6);
  --scrollbar-track: #2d2d2d;
  --scrollbar-thumb: #666;
}
* { scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track); }
::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-track { background: var(--scrollbar-track); }
::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 6px; }

body { background: var(--bg-body); padding: 20px; font-family: 'Segoe UI', system-ui, sans-serif; color: var(--text-primary); transition: all 0.2s; }
.container { max-width: 1400px; }
.header { background: var(--header-bg); color: var(--header-text); padding: 20px; border-radius: 12px; margin-bottom: 25px; box-shadow: var(--header-shadow); }
.header h1 { margin: 0; font-weight: 700; letter-spacing: -0.5px; text-shadow: 0 2px 4px rgba(0,0,0,0.2); }
.header p { margin: 0; opacity: 0.9; }
.card { background: var(--bg-card); border: 1px solid var(--border-card); box-shadow: var(--shadow); color: var(--text-primary); }
.card-header { background: transparent; color: var(--text-primary); border-bottom: 1px solid var(--border-card); }
textarea { font-family: 'Courier New', monospace; font-size: 14px; background: var(--input-bg); color: var(--input-text); border: 1px solid var(--input-border); border-radius: 8px; }
textarea::placeholder { color: var(--input-placeholder); }
.input-area, .output-area { height: 500px; }
.btn-deobfuscate { background: var(--btn-bg); color: var(--btn-text); border: none; font-weight: 600; transition: 0.2s; }
.btn-deobfuscate:hover { background: var(--btn-hover); color: var(--btn-text); transform: scale(1.02); }
.btn-outline-secondary, .btn-outline-success { color: var(--text-primary); border-color: var(--border-card); }
.btn-outline-secondary:hover, .btn-outline-success:hover { background: var(--border-card); color: var(--text-primary); }
.upload-area { border: 2px dashed var(--upload-border); border-radius: 8px; padding: 20px; text-align: center; cursor: pointer; transition: 0.2s; background: var(--upload-bg); color: var(--upload-text); }
.upload-area:hover { border-color: var(--upload-hover); background: rgba(255,255,255,0.05); }
.upload-area small { color: var(--input-placeholder); }
.theme-selector { position: fixed; top: 20px; right: 20px; z-index: 1000; }
.theme-selector select { background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border-card); border-radius: 8px; padding: 8px 16px; font-size: 14px; cursor: pointer; }
.theme-selector select option { background: var(--bg-card); color: var(--text-primary); }
.status { color: var(--text-secondary); }
</style>
</head>
<body>
<div class="theme-selector">
<select id="themeSwitcher">
<option value="ember">🔥 Ember</option>
<option value="burningblack">🖤 Burning Black</option>
<option value="inferno">🔥 Inferno</option>
<option value="nightfire">🌙 Nightfire</option>
<option value="cyberpunk">💜 Cyberpunk Inferno</option>
</select>
</div>
<div class="container">
<div class="header">
<h1>LuaObfuscator ChaoticGood Deobfuscator</h1>
<p class="mb-0">Paste or upload your obfuscated Lua code below</p>
</div>
<div class="row">
<div class="col-md-6">
<div class="card shadow-sm">
<div class="card-header fw-bold">Input</div>
<div class="card-body">
<div class="upload-area" id="dropzone">
<label for="fileinput" class="d-block" style="cursor:pointer;">
<span style="font-size: 2rem;">📁</span><br>
Click to select a .lua file<br>
<small>or drag & drop</small>
</label>
<input type="file" id="fileinput" accept=".lua,.txt" style="display:none;">
</div>
<textarea id="inputcode" class="form-control input-area mt-3" placeholder="-- paste your obfuscated Lua code here"></textarea>
</div>
</div>
</div>
<div class="col-md-6">
<div class="card shadow-sm">
<div class="card-header fw-bold">Output</div>
<div class="card-body">
<textarea id="outputcode" class="form-control output-area" readonly placeholder="deobfuscated code will appear here" style="font-family: 'Courier New', monospace;"></textarea>
<div class="d-flex gap-2 mt-3">
<button id="deobfbtn" class="btn btn-deobfuscate flex-grow-1">🎣 Deobfuscate</button>
<button id="copybtn" class="btn btn-outline-secondary">📋 Copy</button>
<button id="downloadbtn" class="btn btn-outline-success">⬇ Download</button>
</div>
<div id="status" class="mt-2 text-muted small status"></div>
</div>
</div>
</div>
</div>
</div>
<script>
const themes = {
  ember: {
    '--bg-body': '#1a1a1a',
    '--bg-card': '#2d2d2d',
    '--border-card': '#444',
    '--text-primary': '#e0e0e0',
    '--text-secondary': '#aaa',
    '--header-bg': 'linear-gradient(135deg, #f7971e 0%, #ffd200 100%)',
    '--header-text': '#1a1a1a',
    '--header-shadow': '0 8px 32px rgba(0,0,0,0.5)',
    '--input-bg': '#1e1e1e',
    '--input-text': '#e0e0e0',
    '--input-border': '#444',
    '--input-placeholder': '#888',
    '--btn-bg': '#f7971e',
    '--btn-hover': '#d6851a',
    '--btn-text': '#1a1a1a',
    '--upload-border': '#666',
    '--upload-hover': '#f7971e',
    '--upload-bg': '#2d2d2d',
    '--upload-text': '#e0e0e0',
    '--shadow': '0 4px 20px rgba(0,0,0,0.6)',
    '--scrollbar-track': '#2d2d2d',
    '--scrollbar-thumb': '#666'
  },
  burningblack: {
    '--bg-body': '#0a0a0a',
    '--bg-card': '#111111',
    '--border-card': '#2a2a2a',
    '--text-primary': '#ccbbaa',
    '--text-secondary': '#887766',
    '--header-bg': 'linear-gradient(135deg, #1a0a00 0%, #3d1a00 100%)',
    '--header-text': '#ff6a00',
    '--header-shadow': '0 8px 32px rgba(255,69,0,0.3)',
    '--input-bg': '#0a0a0a',
    '--input-text': '#ccbbaa',
    '--input-border': '#2a1a0a',
    '--input-placeholder': '#554433',
    '--btn-bg': '#ff4500',
    '--btn-hover': '#cc3700',
    '--btn-text': '#ffffff',
    '--upload-border': '#3a1a00',
    '--upload-hover': '#ff4500',
    '--upload-bg': '#0d0d0d',
    '--upload-text': '#ccbbaa',
    '--shadow': '0 4px 20px rgba(255,69,0,0.2)',
    '--scrollbar-track': '#111',
    '--scrollbar-thumb': '#3a1a00'
  },
  inferno: {
    '--bg-body': '#1a0a05',
    '--bg-card': '#2a1208',
    '--border-card': '#662200',
    '--text-primary': '#ffccaa',
    '--text-secondary': '#aa7755',
    '--header-bg': 'linear-gradient(135deg, #ff0000 0%, #ff6600 50%, #ffcc00 100%)',
    '--header-text': '#ffffff',
    '--header-shadow': '0 8px 32px rgba(255,0,0,0.4)',
    '--input-bg': '#0d0502',
    '--input-text': '#ffccaa',
    '--input-border': '#441100',
    '--input-placeholder': '#663322',
    '--btn-bg': '#ff3300',
    '--btn-hover': '#cc2900',
    '--btn-text': '#ffffff',
    '--upload-border': '#662200',
    '--upload-hover': '#ff3300',
    '--upload-bg': '#1a0a05',
    '--upload-text': '#ffccaa',
    '--shadow': '0 4px 20px rgba(255,51,0,0.3)',
    '--scrollbar-track': '#1a0a05',
    '--scrollbar-thumb': '#662200'
  },
  nightfire: {
    '--bg-body': '#0d0d0f',
    '--bg-card': '#14141a',
    '--border-card': '#2a2a40',
    '--text-primary': '#c8c0b0',
    '--text-secondary': '#8888aa',
    '--header-bg': 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    '--header-text': '#e0a96d',
    '--header-shadow': '0 8px 32px rgba(224,169,109,0.2)',
    '--input-bg': '#08080c',
    '--input-text': '#c8c0b0',
    '--input-border': '#1a1a2e',
    '--input-placeholder': '#555566',
    '--btn-bg': '#e07c1a',
    '--btn-hover': '#b86212',
    '--btn-text': '#ffffff',
    '--upload-border': '#2a2a40',
    '--upload-hover': '#e07c1a',
    '--upload-bg': '#0d0d12',
    '--upload-text': '#c8c0b0',
    '--shadow': '0 4px 20px rgba(224,169,109,0.1)',
    '--scrollbar-track': '#0d0d0f',
    '--scrollbar-thumb': '#2a2a40'
  },
  cyberpunk: {
    '--bg-body': '#0a0510',
    '--bg-card': '#120a1a',
    '--border-card': '#3a1a4a',
    '--text-primary': '#ffccdd',
    '--text-secondary': '#aa88bb',
    '--header-bg': 'linear-gradient(135deg, #ff007f 0%, #ff5500 50%, #ffaa00 100%)',
    '--header-text': '#ffffff',
    '--header-shadow': '0 8px 32px rgba(255,0,127,0.4)',
    '--input-bg': '#05020a',
    '--input-text': '#ffccdd',
    '--input-border': '#2a0a3a',
    '--input-placeholder': '#663366',
    '--btn-bg': '#ff007f',
    '--btn-hover': '#cc0066',
    '--btn-text': '#ffffff',
    '--upload-border': '#4a1a5a',
    '--upload-hover': '#ff007f',
    '--upload-bg': '#0a0510',
    '--upload-text': '#ffccdd',
    '--shadow': '0 4px 20px rgba(255,0,127,0.3)',
    '--scrollbar-track': '#0a0510',
    '--scrollbar-thumb': '#3a1a4a'
  }
};

const root = document.documentElement;
document.getElementById('themeSwitcher').addEventListener('change', function() {
  const theme = themes[this.value];
  if (!theme) return;
  for (const [key, value] of Object.entries(theme)) {
    root.style.setProperty(key, value);
  }
});
</script>
<script>
const inputBox = document.getElementById('inputcode');
const outputBox = document.getElementById('outputcode');
const deobfBtn = document.getElementById('deobfbtn');
const copyBtn = document.getElementById('copybtn');
const downloadBtn = document.getElementById('downloadbtn');
const statusDiv = document.getElementById('status');
const fileInput = document.getElementById('fileinput');
const dropzone = document.getElementById('dropzone');

fileInput.addEventListener('change', function(e) {
if (this.files.length) {
const reader = new FileReader();
reader.onload = function(ev) { inputBox.value = ev.target.result; statusDiv.textContent = 'Loaded: ' + fileInput.files[0].name; };
reader.readAsText(this.files[0]);
}
});

dropzone.addEventListener('dragover', function(e) { e.preventDefault(); this.style.borderColor = '#f7971e'; });
dropzone.addEventListener('dragleave', function(e) { this.style.borderColor = '#666'; });
dropzone.addEventListener('drop', function(e) {
e.preventDefault();
this.style.borderColor = '#666';
const files = e.dataTransfer.files;
if (files.length) {
const reader = new FileReader();
reader.onload = function(ev) { inputBox.value = ev.target.result; statusDiv.textContent = 'Loaded: ' + files[0].name; };
reader.readAsText(files[0]);
}
});
dropzone.addEventListener('click', function() { fileInput.click(); });

deobfBtn.addEventListener('click', function() {
const code = inputBox.value.trim();
if (!code) { statusDiv.textContent = '⚠ Please enter some code.'; return; }
statusDiv.textContent = '⏳ Deobfuscating...';
deobfBtn.disabled = true;
fetch('/deobfuscate', {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ code: code })
})
.then(res => res.json())
.then(data => {
if (data.error) {
outputBox.value = 'Error: ' + data.error;
statusDiv.textContent = '❌ Failed.';
} else {
outputBox.value = data.result;
statusDiv.textContent = '✅ Deobfuscation complete.';
}
})
.catch(err => {
outputBox.value = 'Error: ' + err;
statusDiv.textContent = '❌ Server error.';
})
.finally(() => { deobfBtn.disabled = false; });
});

copyBtn.addEventListener('click', function() {
const val = outputBox.value;
if (!val) { statusDiv.textContent = 'Nothing to copy.'; return; }
navigator.clipboard.writeText(val).then(() => { statusDiv.textContent = '📋 Copied!'; }).catch(() => { statusDiv.textContent = 'Failed to copy.'; });
});

downloadBtn.addEventListener('click', function() {
const val = outputBox.value;
if (!val) { statusDiv.textContent = 'Nothing to download.'; return; }
const blob = new Blob([val], { type: 'text/plain' });
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'deobfuscated.lua';
document.body.appendChild(a);
a.click();
document.body.removeChild(a);
URL.revokeObjectURL(url);
statusDiv.textContent = '⬇ Download started.';
});
</script>
</body>
</html>
"""

class webhandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(htmlpage.encode("utf-8"))

    def do_POST(self):
        if self.path != "/deobfuscate":
            self.send_response(404)
            self.end_headers()
            return
        contentlen = int(self.headers.get("content-length", 0))
        body = self.rfile.read(contentlen).decode("utf-8")
        try:
            data = json.loads(body)
            code = data.get("code", "")
        except:
            self.send_error(400, "invalid json")
            return
        result = deobfuscatechaoticgood(code)
        if result is None:
            response = {"error": "not chaotic good obfuscation or deobfuscation failed"}
        else:
            response = {"result": result}
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def log_message(self, format, *args):
        pass

def launchweb(port=8080):
    socketserver.TCPServer.allow_reuse_address = True
    for attempt in range(10):
        try:
            with socketserver.TCPServer(("", port + attempt), webhandler) as httpd:
                actual_port = port + attempt
                print(f"server running at http://localhost:{actual_port}")
                webbrowser.open(f"http://localhost:{actual_port}")
                try:
                    httpd.serve_forever()
                except keyboardinterrupt:
                    print("\nshutting down...")
                return
        except OSError as e:
            if "Address already in use" in str(e):
                continue
            else:
                raise
    print(f"Could not find an available port near {port}. Try a different port with --port <number>")
    sys.exit(1)

if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1 and sys.argv[1] == "--port":
        try:
            port = int(sys.argv[2])
        except:
            print("usage: python webui.py [--port <number>]")
            sys.exit(1)
    launchweb(port)
