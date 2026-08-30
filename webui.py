import http.server
import socketserver
import json
import webbrowser
import urllib.parse
import sys
from deobfuscate import deobfuscatechaotic

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
  --status-text: #aaa;
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
.status { color: var(--status-text) !important; }
</style>
</head>
<body>
<div class="theme-selector">
<select id="themeSwitcher">
<optgroup label="🔥 Dark Fire">
<option value="ember">Ember</option>
<option value="burningblack">Burning Black</option>
<option value="inferno">Inferno</option>
<option value="nightfire">Nightfire</option>
<option value="cyberpunk">Cyberpunk Inferno</option>
<option value="volcanic">Volcanic</option>
<option value="darkvoid">Dark Void</option>
</optgroup>
<optgroup label="☀️ Light Fire">
<option value="lightember">Light Ember</option>
<option value="lightinferno">Light Inferno</option>
<option value="lightfire">Light Fire</option>
<option value="lightcyberpunk">Light Cyberpunk</option>
<option value="lightrose">Light Rose</option>
<option value="lightcitrus">Light Citrus</option>
<option value="lightlava">Light Lava</option>
</optgroup>
<optgroup label="🎨 Other">
<option value="classic">Classic</option>
</optgroup>
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
<div class="d-flex flex-wrap gap-3 mt-3 align-items-center">
<div class="d-flex gap-3">
<label class="option-check"><input type="checkbox" id="cbbeautify" checked> Beautify</label>
<label class="option-check"><input type="checkbox" id="cbremovedead" checked> Remove Dead Loops</label>
</div>
<button id="deobfbtn" class="btn btn-deobfuscate flex-grow-1">🎣 Deobfuscate</button>
</div>
<div class="d-flex gap-2 mt-2">
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
    '--bg-body': '#1a1a1a', '--bg-card': '#2d2d2d', '--border-card': '#444',
    '--text-primary': '#e0e0e0', '--text-secondary': '#aaa', '--status-text': '#aaa',
    '--header-bg': 'linear-gradient(135deg, #f7971e 0%, #ffd200 100%)',
    '--header-text': '#1a1a1a', '--header-shadow': '0 8px 32px rgba(0,0,0,0.5)',
    '--input-bg': '#1e1e1e', '--input-text': '#e0e0e0', '--input-border': '#444',
    '--input-placeholder': '#888', '--btn-bg': '#f7971e', '--btn-hover': '#d6851a',
    '--btn-text': '#1a1a1a', '--upload-border': '#666', '--upload-hover': '#f7971e',
    '--upload-bg': '#2d2d2d', '--upload-text': '#e0e0e0',
    '--shadow': '0 4px 20px rgba(0,0,0,0.6)',
    '--scrollbar-track': '#2d2d2d', '--scrollbar-thumb': '#666'
  },
  burningblack: {
    '--bg-body': '#0a0a0a', '--bg-card': '#111111', '--border-card': '#2a2a2a',
    '--text-primary': '#e0e0e0', '--text-secondary': '#887766', '--status-text': '#887766',
    '--header-bg': 'linear-gradient(135deg, #1a0a00 0%, #3d1a00 100%)',
    '--header-text': '#ff6a00', '--header-shadow': '0 8px 32px rgba(255,69,0,0.3)',
    '--input-bg': '#0a0a0a', '--input-text': '#e0e0e0', '--input-border': '#2a1a0a',
    '--input-placeholder': '#554433', '--btn-bg': '#ff4500', '--btn-hover': '#cc3700',
    '--btn-text': '#ffffff', '--upload-border': '#3a1a00', '--upload-hover': '#ff4500',
    '--upload-bg': '#0d0d0d', '--upload-text': '#e0e0e0',
    '--shadow': '0 4px 20px rgba(255,69,0,0.2)',
    '--scrollbar-track': '#111', '--scrollbar-thumb': '#3a1a00'
  },
  inferno: {
    '--bg-body': '#1a0a05', '--bg-card': '#2a1208', '--border-card': '#662200',
    '--text-primary': '#e0e0e0', '--text-secondary': '#aa7755', '--status-text': '#aa7755',
    '--header-bg': 'linear-gradient(135deg, #ff0000 0%, #ff6600 50%, #ffcc00 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(255,0,0,0.4)',
    '--input-bg': '#0d0502', '--input-text': '#e0e0e0', '--input-border': '#441100',
    '--input-placeholder': '#663322', '--btn-bg': '#ff3300', '--btn-hover': '#cc2900',
    '--btn-text': '#ffffff', '--upload-border': '#662200', '--upload-hover': '#ff3300',
    '--upload-bg': '#1a0a05', '--upload-text': '#e0e0e0',
    '--shadow': '0 4px 20px rgba(255,51,0,0.3)',
    '--scrollbar-track': '#1a0a05', '--scrollbar-thumb': '#662200'
  },
  nightfire: {
    '--bg-body': '#0d0d0f', '--bg-card': '#14141a', '--border-card': '#2a2a40',
    '--text-primary': '#e0e0e0', '--text-secondary': '#8888aa', '--status-text': '#8888aa',
    '--header-bg': 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
    '--header-text': '#e0a96d', '--header-shadow': '0 8px 32px rgba(224,169,109,0.2)',
    '--input-bg': '#08080c', '--input-text': '#e0e0e0', '--input-border': '#1a1a2e',
    '--input-placeholder': '#555566', '--btn-bg': '#e07c1a', '--btn-hover': '#b86212',
    '--btn-text': '#ffffff', '--upload-border': '#2a2a40', '--upload-hover': '#e07c1a',
    '--upload-bg': '#0d0d12', '--upload-text': '#e0e0e0',
    '--shadow': '0 4px 20px rgba(224,169,109,0.1)',
    '--scrollbar-track': '#0d0d0f', '--scrollbar-thumb': '#2a2a40'
  },
  cyberpunk: {
    '--bg-body': '#0a0510', '--bg-card': '#120a1a', '--border-card': '#3a1a4a',
    '--text-primary': '#e0e0e0', '--text-secondary': '#aa88bb', '--status-text': '#aa88bb',
    '--header-bg': 'linear-gradient(135deg, #ff007f 0%, #ff5500 50%, #ffaa00 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(255,0,127,0.4)',
    '--input-bg': '#05020a', '--input-text': '#e0e0e0', '--input-border': '#2a0a3a',
    '--input-placeholder': '#663366', '--btn-bg': '#ff007f', '--btn-hover': '#cc0066',
    '--btn-text': '#ffffff', '--upload-border': '#4a1a5a', '--upload-hover': '#ff007f',
    '--upload-bg': '#0a0510', '--upload-text': '#e0e0e0',
    '--shadow': '0 4px 20px rgba(255,0,127,0.3)',
    '--scrollbar-track': '#0a0510', '--scrollbar-thumb': '#3a1a4a'
  },
  volcanic: {
    '--bg-body': '#1a0a05', '--bg-card': '#2a0f0a', '--border-card': '#8b3a2a',
    '--text-primary': '#e0e0e0', '--text-secondary': '#cc8855', '--status-text': '#cc8855',
    '--header-bg': 'linear-gradient(135deg, #8b0000 0%, #ff4500 50%, #ff6a00 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(139,0,0,0.6)',
    '--input-bg': '#1a0a05', '--input-text': '#e0e0e0', '--input-border': '#8b3a2a',
    '--input-placeholder': '#8b3a2a', '--btn-bg': '#8b0000', '--btn-hover': '#ff4500',
    '--btn-text': '#ffffff', '--upload-border': '#8b3a2a', '--upload-hover': '#ff4500',
    '--upload-bg': '#2a0f0a', '--upload-text': '#e0e0e0',
    '--shadow': '0 4px 20px rgba(139,0,0,0.4)',
    '--scrollbar-track': '#1a0a05', '--scrollbar-thumb': '#8b3a2a'
  },
  darkvoid: {
    '--bg-body': '#000000', '--bg-card': '#0a0a0a', '--border-card': '#1a1a1a',
    '--text-primary': '#e0e0e0', '--text-secondary': '#888888', '--status-text': '#888888',
    '--header-bg': 'linear-gradient(135deg, #111 0%, #222 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(255,255,255,0.05)',
    '--input-bg': '#050505', '--input-text': '#e0e0e0', '--input-border': '#1a1a1a',
    '--input-placeholder': '#444', '--btn-bg': '#333', '--btn-hover': '#555',
    '--btn-text': '#ffffff', '--upload-border': '#222', '--upload-hover': '#555',
    '--upload-bg': '#0a0a0a', '--upload-text': '#e0e0e0',
    '--shadow': '0 4px 20px rgba(0,0,0,0.8)',
    '--scrollbar-track': '#0a0a0a', '--scrollbar-thumb': '#222'
  },
  lightember: {
    '--bg-body': '#f5f0e8', '--bg-card': '#ffffff', '--border-card': '#e0d5c8',
    '--text-primary': '#212529', '--text-secondary': '#8a7a6a', '--status-text': '#8a7a6a',
    '--header-bg': 'linear-gradient(135deg, #f7971e 0%, #ffd200 100%)',
    '--header-text': '#1a1a1a', '--header-shadow': '0 8px 32px rgba(247,151,30,0.3)',
    '--input-bg': '#faf8f5', '--input-text': '#212529', '--input-border': '#e0d5c8',
    '--input-placeholder': '#b0a090', '--btn-bg': '#f7971e', '--btn-hover': '#d6851a',
    '--btn-text': '#1a1a1a', '--upload-border': '#d5c8b8', '--upload-hover': '#f7971e',
    '--upload-bg': '#faf8f5', '--upload-text': '#212529',
    '--shadow': '0 4px 20px rgba(0,0,0,0.08)',
    '--scrollbar-track': '#f0e8dc', '--scrollbar-thumb': '#d5c8b8'
  },
  lightinferno: {
    '--bg-body': '#f5e8e0', '--bg-card': '#ffffff', '--border-card': '#e8c8b0',
    '--text-primary': '#212529', '--text-secondary': '#8a5a3a', '--status-text': '#8a5a3a',
    '--header-bg': 'linear-gradient(135deg, #ff3300 0%, #ff8800 50%, #ffcc00 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(255,51,0,0.3)',
    '--input-bg': '#fdf8f5', '--input-text': '#212529', '--input-border': '#e8c8b0',
    '--input-placeholder': '#b08a70', '--btn-bg': '#ff3300', '--btn-hover': '#cc2900',
    '--btn-text': '#ffffff', '--upload-border': '#e8c8b0', '--upload-hover': '#ff3300',
    '--upload-bg': '#fdf8f5', '--upload-text': '#212529',
    '--shadow': '0 4px 20px rgba(0,0,0,0.08)',
    '--scrollbar-track': '#f0e0d0', '--scrollbar-thumb': '#e8c8b0'
  },
  lightfire: {
    '--bg-body': '#faf0e8', '--bg-card': '#ffffff', '--border-card': '#f0d8c0',
    '--text-primary': '#212529', '--text-secondary': '#8a6a4a', '--status-text': '#8a6a4a',
    '--header-bg': 'linear-gradient(135deg, #ff6a00 0%, #ffaa00 50%, #ffdd00 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(255,106,0,0.3)',
    '--input-bg': '#fffcf8', '--input-text': '#212529', '--input-border': '#f0d8c0',
    '--input-placeholder': '#b09070', '--btn-bg': '#ff6a00', '--btn-hover': '#cc5500',
    '--btn-text': '#ffffff', '--upload-border': '#f0d8c0', '--upload-hover': '#ff6a00',
    '--upload-bg': '#fffcf8', '--upload-text': '#212529',
    '--shadow': '0 4px 20px rgba(0,0,0,0.06)',
    '--scrollbar-track': '#f5ece0', '--scrollbar-thumb': '#f0d8c0'
  },
  lightcyberpunk: {
    '--bg-body': '#f5f0f8', '--bg-card': '#ffffff', '--border-card': '#e8d0f0',
    '--text-primary': '#212529', '--text-secondary': '#8a6a9a', '--status-text': '#8a6a9a',
    '--header-bg': 'linear-gradient(135deg, #ff007f 0%, #ff5500 50%, #ffaa00 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(255,0,127,0.2)',
    '--input-bg': '#fcf8ff', '--input-text': '#212529', '--input-border': '#e8d0f0',
    '--input-placeholder': '#b090b0', '--btn-bg': '#ff007f', '--btn-hover': '#cc0066',
    '--btn-text': '#ffffff', '--upload-border': '#e8d0f0', '--upload-hover': '#ff007f',
    '--upload-bg': '#fcf8ff', '--upload-text': '#212529',
    '--shadow': '0 4px 20px rgba(0,0,0,0.06)',
    '--scrollbar-track': '#f0ecf5', '--scrollbar-thumb': '#e8d0f0'
  },
  lightrose: {
    '--bg-body': '#fdf5f5', '--bg-card': '#ffffff', '--border-card': '#f0d8d8',
    '--text-primary': '#212529', '--text-secondary': '#8a6a6a', '--status-text': '#8a6a6a',
    '--header-bg': 'linear-gradient(135deg, #ff6b8a 0%, #ffb3b3 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(255,107,138,0.3)',
    '--input-bg': '#fffafa', '--input-text': '#212529', '--input-border': '#f0d8d8',
    '--input-placeholder': '#b09090', '--btn-bg': '#ff6b8a', '--btn-hover': '#e05575',
    '--btn-text': '#ffffff', '--upload-border': '#f0d8d8', '--upload-hover': '#ff6b8a',
    '--upload-bg': '#fffafa', '--upload-text': '#212529',
    '--shadow': '0 4px 20px rgba(0,0,0,0.06)',
    '--scrollbar-track': '#f8f0f0', '--scrollbar-thumb': '#f0d8d8'
  },
  lightcitrus: {
    '--bg-body': '#f8f5e8', '--bg-card': '#ffffff', '--border-card': '#f0e8c8',
    '--text-primary': '#212529', '--text-secondary': '#8a8a4a', '--status-text': '#8a8a4a',
    '--header-bg': 'linear-gradient(135deg, #ffdd00 0%, #ff8800 100%)',
    '--header-text': '#1a1a0a', '--header-shadow': '0 8px 32px rgba(255,221,0,0.3)',
    '--input-bg': '#fdfcf5', '--input-text': '#212529', '--input-border': '#f0e8c8',
    '--input-placeholder': '#b0a870', '--btn-bg': '#ffdd00', '--btn-hover': '#e6c400',
    '--btn-text': '#1a1a0a', '--upload-border': '#f0e8c8', '--upload-hover': '#ffdd00',
    '--upload-bg': '#fdfcf5', '--upload-text': '#212529',
    '--shadow': '0 4px 20px rgba(0,0,0,0.06)',
    '--scrollbar-track': '#f5f0e0', '--scrollbar-thumb': '#f0e8c8'
  },
  lightlava: {
    '--bg-body': '#f5ece0', '--bg-card': '#ffffff', '--border-card': '#e8d0b8',
    '--text-primary': '#212529', '--text-secondary': '#8a6a4a', '--status-text': '#8a6a4a',
    '--header-bg': 'linear-gradient(135deg, #ff4500 0%, #ff6a00 50%, #ff8800 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(255,69,0,0.2)',
    '--input-bg': '#fcf8f0', '--input-text': '#212529', '--input-border': '#e8d0b8',
    '--input-placeholder': '#b09878', '--btn-bg': '#ff4500', '--btn-hover': '#cc3700',
    '--btn-text': '#ffffff', '--upload-border': '#e8d0b8', '--upload-hover': '#ff4500',
    '--upload-bg': '#fcf8f0', '--upload-text': '#212529',
    '--shadow': '0 4px 20px rgba(0,0,0,0.06)',
    '--scrollbar-track': '#f5ece0', '--scrollbar-thumb': '#e8d0b8'
  },
  classic: {
    '--bg-body': '#f8f9fa', '--bg-card': '#ffffff', '--border-card': '#dee2e6',
    '--text-primary': '#212529', '--text-secondary': '#6c757d', '--status-text': '#6c757d',
    '--header-bg': 'linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%)',
    '--header-text': '#ffffff', '--header-shadow': '0 8px 32px rgba(13,110,253,0.3)',
    '--input-bg': '#ffffff', '--input-text': '#212529', '--input-border': '#ced4da',
    '--input-placeholder': '#6c757d', '--btn-bg': '#0d6efd', '--btn-hover': '#0a58ca',
    '--btn-text': '#ffffff', '--upload-border': '#ced4da', '--upload-hover': '#0d6efd',
    '--upload-bg': '#ffffff', '--upload-text': '#212529',
    '--shadow': '0 4px 20px rgba(0,0,0,0.08)',
    '--scrollbar-track': '#f1f3f5', '--scrollbar-thumb': '#ced4da'
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
const cbbeautify = document.getElementById('cbbeautify');
const cbremovedead = document.getElementById('cbremovedead');

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
body: JSON.stringify({
code: code,
beautify: cbbeautify.checked,
removedead: cbremovedead.checked
})
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
outputBox.value = 'Error: ' + err.message;
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
            beautify = data.get("beautify", True)
            removedead = data.get("removedead", True)
        except:
            self.send_error(400, "invalid json")
            return
        try:
            result = deobfuscatechaotic(code)
            if result is None:
                response = {"error": "not chaotic good obfuscation or deobfuscation failed"}
            else:
                response = {"result": result}
        except Exception as e:
            response = {"error": str(e)}
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
                except KeyboardInterrupt:
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
