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
<style>
body { background: #f8f9fa; padding: 20px; }
.container { max-width: 1400px; }
.header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 25px; }
.header h1 { margin: 0; font-weight: 300; }
textarea { font-family: 'Courier New', monospace; font-size: 14px; }
.input-area, .output-area { height: 500px; }
.btn-deobfuscate { background: #764ba2; color: white; }
.btn-deobfuscate:hover { background: #5a3a7a; color: white; }
.upload-area { border: 2px dashed #ced4da; border-radius: 8px; padding: 20px; text-align: center; cursor: pointer; transition: 0.2s; }
.upload-area:hover { border-color: #764ba2; background: #f3f0ff; }
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>LuaObfuscator Chaotic Good Deobfuscator</h1>
<p class="mb-0">Paste or upload your obfuscated Lua code below</p>
</div>
<div class="row">
<div class="col-md-6">
<div class="card shadow-sm">
<div class="card-header bg-white fw-bold">Input</div>
<div class="card-body">
<div class="upload-area" id="dropzone">
<label for="fileinput" class="d-block" style="cursor:pointer;">
<span style="font-size: 2rem;">📁</span><br>
Click to select a .lua file<br>
<small class="text-muted">or drag & drop</small>
</label>
<input type="file" id="fileinput" accept=".lua,.txt" style="display:none;">
</div>
<textarea id="inputcode" class="form-control input-area mt-3" placeholder="-- paste your obfuscated Lua code here"></textarea>
</div>
</div>
</div>
<div class="col-md-6">
<div class="card shadow-sm">
<div class="card-header bg-white fw-bold">Output</div>
<div class="card-body">
<textarea id="outputcode" class="form-control output-area" readonly placeholder="deobfuscated code will appear here"></textarea>
<div class="d-flex gap-2 mt-3">
<button id="deobfbtn" class="btn btn-deobfuscate flex-grow-1">🎣 Deobfuscate</button>
<button id="copybtn" class="btn btn-outline-secondary">📋 Copy</button>
<button id="downloadbtn" class="btn btn-outline-success">⬇ Download</button>
</div>
<div id="status" class="mt-2 text-muted small"></div>
</div>
</div>
</div>
</div>
</div>
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

dropzone.addEventListener('dragover', function(e) { e.preventDefault(); this.style.borderColor = '#764ba2'; });
dropzone.addEventListener('dragleave', function(e) { this.style.borderColor = '#ced4da'; });
dropzone.addEventListener('drop', function(e) {
e.preventDefault();
this.style.borderColor = '#ced4da';
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
    def do_get(self):
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(htmlpage.encode("utf-8"))

    def do_post(self):
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
    with socketserver.tcpserver(("", port), webhandler) as httpd:
        print(f"server running at http://localhost:{port}")
        webbrowser.open(f"http://localhost:{port}")
        try:
            httpd.serve_forever()
        except keyboardinterrupt:
            print("\nshutting down...")

if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1 and sys.argv[1] == "--port":
        try: port = int(sys.argv[2])
        except: pass
    launchweb(port)
