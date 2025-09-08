# server.py
import os
from flask import Flask, request, send_from_directory, render_template_string, url_for, redirect

# Inizializza l'applicazione Flask
app = Flask(__name__)

# Definisci la cartella dove verranno salvati i file caricati
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Assicurati che la cartella di upload esista
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Template HTML per la pagina principale con il form di upload e l'elenco dei file
HTML_TEMPLATE = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
  <title>File Server</title>
  <style>
    body { font-family: sans-serif; margin: 2em; background-color: #f4f4f9; }
    .container { max-width: 800px; margin: auto; background: white; padding: 2em; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    h1, h2 { color: #333; }
    input[type="file"], input[type="submit"] { margin-top: 1em; }
    ul { list-style-type: none; padding: 0; }
    li { margin: 0.5em 0; padding: 0.5em; background: #eee; border-radius: 4px; }
    a { text-decoration: none; color: #007bff; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Carica File</h1>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="files" multiple>
      <input type="submit" value="Carica">
    </form>
    <hr style="margin-top: 2em; margin-bottom: 2em;">
    <h2>File Disponibili per il Download</h2>
    <ul>
      {% for file in files %}
        <li><a href="{{ url_for('download_file', filename=file) }}">{{ file }}</a></li>
      {% else %}
        <li>Nessun file disponibile.</li>
      {% endfor %}
    </ul>
  </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Controlla se la richiesta POST ha la parte del file
        if 'files' not in request.files:
            return redirect(request.url)
        
        files = request.files.getlist('files')
        
        for file in files:
            # Se l'utente non seleziona un file, il browser invia
            # una parte vuota senza nome file
            if file.filename == '':
                continue
            if file:
                filename = file.filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        return redirect(url_for('index'))

    # Per la richiesta GET, mostra la pagina di upload e l'elenco dei file
    uploaded_files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template_string(HTML_TEMPLATE, files=uploaded_files)

@app.route('/download/<path:filename>')
def download_file(filename):
    """
    Endpoint per scaricare un file dalla cartella di upload.
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    # Esegui l'app rendendola accessibile da altri dispositivi nella stessa rete
    # usando l'indirizzo IP locale del tuo computer.
    # Usa la porta 5000.
    app.run(host='0.0.0.0', port=5000, debug=True)