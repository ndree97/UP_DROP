# UP DROP - file server con dashboard di controllo
import os
import shutil
import time
from flask import Flask, request, send_from_directory, jsonify, render_template_string
from werkzeug.utils import safe_join

app = Flask(__name__)

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
# "active" = file correnti, "old" = archivio (la cartella uploads/old esistente)
DIRS = {'active': BASE, 'old': os.path.join(BASE, 'old')}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)


def path_of(area, name):
    """Percorso sicuro di un file (blocca path traversal) o None."""
    if area not in DIRS or not name or os.path.basename(name) != name:
        return None
    p = safe_join(DIRS[area], name)
    return p if p and os.path.isfile(p) else None


def unique(folder, name):
    """Evita di sovrascrivere: file.txt -> file (1).txt"""
    stem, ext = os.path.splitext(name)
    n, out = 1, name
    while os.path.exists(os.path.join(folder, out)):
        out = f'{stem} ({n}){ext}'
        n += 1
    return out


def move(area, name, to):
    src = path_of(area, name)
    if src and area != to:
        shutil.move(src, os.path.join(DIRS[to], unique(DIRS[to], name)))
        return True
    return False


HTML = """
<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UP DROP</title>
<style>
:root{--bg:#f3f4f8;--card:#fff;--fg:#1c2033;--mut:#707693;--line:#e4e6ef;--acc:#5b5bf0;--accf:#fff;--ok:#16a34a;--bad:#dc2626;--warn:#d97706}
@media (prefers-color-scheme:dark){:root{--bg:#12141f;--card:#1b1e2e;--fg:#e8eaf6;--mut:#8a90ad;--line:#2b2f45;--acc:#7c7cff;--accf:#12141f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 system-ui,Segoe UI,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:20px 16px 60px}
header{display:flex;align-items:center;gap:10px;margin-bottom:18px}
header h1{margin:0;font-size:1.5rem}header span{color:var(--mut)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.stat b{display:block;font-size:1.6rem}.stat small{color:var(--mut)}
#drop{border:2px dashed var(--line);border-radius:12px;padding:26px;text-align:center;color:var(--mut);cursor:pointer;margin-bottom:16px;transition:.15s}
#drop.over{border-color:var(--acc);background:color-mix(in srgb,var(--acc) 10%,transparent);color:var(--fg)}
#bar{height:6px;border-radius:3px;background:var(--line);margin-top:10px;display:none;overflow:hidden}
#bar i{display:block;height:100%;width:0;background:var(--acc)}
.tools{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
input[type=search],input[type=number],select{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font:inherit}
input[type=search]{flex:1;min-width:160px}input[type=number]{width:70px}
button{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:7px 12px;font:inherit;cursor:pointer}
button:hover{border-color:var(--acc)}button.p{background:var(--acc);color:var(--accf);border-color:var(--acc)}
button.d:hover{border-color:var(--bad);color:var(--bad)}button:disabled{opacity:.4;pointer-events:none}
.tabs button.on{background:var(--acc);color:var(--accf);border-color:var(--acc)}
.tbl{overflow-x:auto;padding:0}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--mut);font-weight:600;font-size:.8rem;text-transform:uppercase;cursor:pointer;user-select:none}
td.n{white-space:normal;word-break:break-all;max-width:420px}
tr:last-child td{border:0}td.a{text-align:right}
.tag{font-size:.72rem;padding:2px 8px;border-radius:99px;background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)}
.tag.old{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.empty{padding:30px;text-align:center;color:var(--mut)}
#toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:var(--fg);color:var(--bg);padding:10px 18px;border-radius:10px;opacity:0;transition:.2s;pointer-events:none}
#toast.on{opacity:1}
</style>
</head>
<body>
<div class="wrap">
  <header><h1>📦 UP DROP</h1><span>dashboard di controllo</span></header>

  <div class="stats" id="stats"></div>

  <div id="drop">Trascina qui i file o clicca per caricarli
    <input type="file" id="pick" multiple hidden><div id="bar"><i></i></div></div>

  <div class="tools">
    <div class="tabs">
      <button data-t="all" class="on">Tutti</button>
      <button data-t="active">Attivi</button>
      <button data-t="old">Archiviati</button>
    </div>
    <input type="search" id="q" placeholder="Cerca file…">
    <button id="bArc" disabled>Archivia</button>
    <button id="bRes" disabled>Ripristina</button>
    <button id="bDel" class="d" disabled>Elimina</button>
  </div>
  <div class="tools">
    <span style="color:var(--mut)">Archivia attivi più vecchi di</span>
    <input type="number" id="days" value="30" min="0"> <span style="color:var(--mut)">giorni</span>
    <button id="bOld">Archivia</button>
  </div>

  <div class="card tbl"><table>
    <thead><tr>
      <th><input type="checkbox" id="all"></th>
      <th data-k="name">Nome</th><th data-k="size">Dimensione</th>
      <th data-k="mtime">Data</th><th data-k="area">Stato</th><th></th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table><div class="empty" id="empty" hidden>Nessun file.</div></div>
</div>
<div id="toast"></div>

<script>
const $=s=>document.querySelector(s);
let files=[], tab='all', sortK='mtime', sortD=-1, sel=new Set();
const key=f=>f.area+'/'+f.name;
const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=b=>{const u=['B','KB','MB','GB','TB'];let i=0;while(b>=1024&&i<4){b/=1024;i++}return b.toFixed(i?1:0)+' '+u[i]};
const date=t=>new Date(t*1000).toLocaleString('it-IT',{dateStyle:'short',timeStyle:'short'});
function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('on');setTimeout(()=>t.classList.remove('on'),2500)}
async function api(url,body){
  const r=await fetch(url,body&&{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json();if(!r.ok)throw new Error(j.error||r.statusText);return j;
}
async function load(){
  const j=await api('/api/files');files=j.files;sel=new Set([...sel].filter(k=>files.some(f=>key(f)==k)));
  const act=files.filter(f=>f.area=='active'),old=files.filter(f=>f.area=='old');
  const sum=a=>a.reduce((s,f)=>s+f.size,0);
  $('#stats').innerHTML=[
    ['File totali',files.length],['Attivi',act.length+' · '+fmt(sum(act))],
    ['Archiviati',old.length+' · '+fmt(sum(old))],['Spazio usato',fmt(sum(files))],
    ['Disco libero',fmt(j.free)]
  ].map(([l,v])=>`<div class="card stat"><small>${l}</small><b>${v}</b></div>`).join('');
  render();
}
function render(){
  const q=$('#q').value.toLowerCase();
  const v=files.filter(f=>(tab=='all'||f.area==tab)&&f.name.toLowerCase().includes(q))
    .sort((a,b)=>(a[sortK]>b[sortK]?1:-1)*sortD);
  $('#rows').innerHTML=v.map(f=>{const k=esc(key(f));return `<tr>
    <td><input type="checkbox" data-k="${k}" ${sel.has(key(f))?'checked':''}></td>
    <td class="n">${esc(f.name)}</td><td>${fmt(f.size)}</td><td>${date(f.mtime)}</td>
    <td><span class="tag ${f.area}">${f.area=='old'?'archiviato':'attivo'}</span></td>
    <td class="a"><a href="/download/${f.area}/${encodeURIComponent(f.name)}"><button>⬇</button></a></td></tr>`}).join('');
  $('#empty').hidden=v.length>0;
  const n=sel.size;['#bArc','#bRes','#bDel'].forEach(b=>$(b).disabled=!n);
  $('#all').checked=v.length>0&&v.every(f=>sel.has(key(f)));
  $('#all').onchange=e=>{v.forEach(f=>e.target.checked?sel.add(key(f)):sel.delete(key(f)));render()};
}
const picked=()=>[...sel].map(k=>{const i=k.indexOf('/');return{area:k.slice(0,i),name:k.slice(i+1)}});
async function act(fn,msg){try{await fn();toast(msg)}catch(e){toast('Errore: '+e.message)}sel.clear();load()}

$('#rows').onchange=e=>{const k=e.target.dataset.k;if(k){e.target.checked?sel.add(k):sel.delete(k);render()}};
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{
  tab=b.dataset.t;document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('on',x==b));render()});
document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{
  sortD=sortK==th.dataset.k?-sortD:1;sortK=th.dataset.k;render()});
$('#q').oninput=render;
$('#bArc').onclick=()=>act(()=>api('/api/move',{items:picked(),to:'old'}),'Archiviati');
$('#bRes').onclick=()=>act(()=>api('/api/move',{items:picked(),to:'active'}),'Ripristinati');
$('#bDel').onclick=()=>{if(confirm(`Eliminare definitivamente ${sel.size} file?`))act(()=>api('/api/delete',{items:picked()}),'Eliminati')};
$('#bOld').onclick=()=>act(async()=>{const j=await api('/api/archive_old',{days:+$('#days').value});toast(j.moved+' file archiviati')},'Fatto');

function upload(list){
  if(!list.length)return;
  const fd=new FormData();[...list].forEach(f=>fd.append('files',f));
  const x=new XMLHttpRequest(),bar=$('#bar'),i=bar.firstChild;bar.style.display='block';
  x.upload.onprogress=e=>i.style.width=(e.loaded/e.total*100)+'%';
  x.onload=()=>{bar.style.display='none';i.style.width=0;toast(x.status==200?'Caricamento completato':'Errore upload');load()};
  x.onerror=()=>{bar.style.display='none';toast('Errore di rete')};
  x.open('POST','/api/upload');x.send(fd);
}
const dz=$('#drop');
dz.onclick=e=>{if(e.target==dz)$('#pick').click()};
$('#pick').onchange=e=>{upload(e.target.files);e.target.value=''};
dz.ondragover=e=>{e.preventDefault();dz.classList.add('over')};
dz.ondragleave=()=>dz.classList.remove('over');
dz.ondrop=e=>{e.preventDefault();dz.classList.remove('over');upload(e.dataTransfer.files)};
load();
</script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/api/files')
def api_files():
    out = []
    for area, d in DIRS.items():
        for e in os.scandir(d):
            if e.is_file():
                st = e.stat()
                out.append({'name': e.name, 'area': area, 'size': st.st_size, 'mtime': st.st_mtime})
    return jsonify(files=out, free=shutil.disk_usage(BASE).free)


@app.route('/api/upload', methods=['POST'])
def api_upload():
    for f in request.files.getlist('files'):
        name = os.path.basename(f.filename.replace('\\', '/'))
        if name:
            f.save(os.path.join(DIRS['active'], unique(DIRS['active'], name)))
    return jsonify(ok=True)


@app.route('/api/move', methods=['POST'])
def api_move():
    data = request.get_json(force=True)
    if data.get('to') not in DIRS:
        return jsonify(error='destinazione non valida'), 400
    n = sum(move(i.get('area'), i.get('name'), data['to']) for i in data.get('items', []))
    return jsonify(moved=n)


@app.route('/api/delete', methods=['POST'])
def api_delete():
    n = 0
    for i in request.get_json(force=True).get('items', []):
        p = path_of(i.get('area'), i.get('name'))
        if p:
            os.remove(p)
            n += 1
    return jsonify(deleted=n)


@app.route('/api/archive_old', methods=['POST'])
def api_archive_old():
    try:
        days = float(request.get_json(force=True).get('days'))
    except (TypeError, ValueError):
        return jsonify(error='giorni non validi'), 400
    limit = time.time() - days * 86400
    n = sum(move('active', e.name, 'old') for e in list(os.scandir(DIRS['active']))
            if e.is_file() and e.stat().st_mtime < limit)
    return jsonify(moved=n)


@app.route('/download/<area>/<path:filename>')
def download_file(area, filename):
    if not path_of(area, filename):
        return jsonify(error='file non trovato'), 404
    return send_from_directory(DIRS[area], filename, as_attachment=True)


if __name__ == '__main__':
    # Accessibile in LAN sulla porta 5000. debug=False: la console Werkzeug in rete permetterebbe di eseguire codice.
    app.run(host='0.0.0.0', port=5000, debug=False)
