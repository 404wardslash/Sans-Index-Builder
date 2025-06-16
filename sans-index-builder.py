from flask import Flask, render_template_string, request, redirect, url_for, jsonify, send_file
from collections import defaultdict
import json
import os
from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

app = Flask(__name__)

ROOT_FOLDER = "indexes"
os.makedirs(ROOT_FOLDER, exist_ok=True)

current_index_folder = None
settings = {}
index_entries = []

def load_current(folder):
    global current_index_folder, settings, index_entries
    current_index_folder = os.path.join(ROOT_FOLDER, folder)
    with open(os.path.join(current_index_folder, "settings.json"), "r") as f:
        settings = json.load(f)
    data_path = os.path.join(current_index_folder, "data.json")
    if os.path.exists(data_path):
        with open(data_path, "r") as f:
            index_entries = json.load(f)
    else:
        index_entries = []

def save_entries():
    with open(os.path.join(current_index_folder, "data.json"), "w") as f:
        json.dump(index_entries, f, indent=4)

def save_settings():
    with open(os.path.join(current_index_folder, "settings.json"), "w") as f:
        json.dump(settings, f, indent=4)

HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Index Home</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma; background: #f4f6f8; padding: 40px; }
        .container { max-width: 600px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 0 15px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        form { margin-bottom: 30px; }
        label { font-weight: bold; }
        input, select { width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 6px; }
        button { padding: 10px 20px; background-color: #0057ff; color: white; border: none; border-radius: 6px; cursor: pointer; }
        button:hover { background-color: #0041c4; }
    </style>
</head>
<body>
    <div class="container">
        <h1>SANS Index Home</h1>
        <form method="POST" action="/create">
            <h3>Create New Index</h3>
            <label>Title</label>
            <input name="title" required autocomplete="off">
            <label>Number of Books</label>
            <input type="number" name="books" required>
            <label>Number of Workbooks</label>
            <input type="number" name="workbooks" required>
            <button type="submit">Create</button>
        </form>
        <form method="POST" action="/load">
            <h3>Work on Existing Index</h3>
            <label>Select Existing Index</label>
            <select name="folder">
                {% for folder in folders %}
                <option value="{{ folder }}">{{ folder }}</option>
                {% endfor %}
            </select>
            <button type="submit">Load</button>
        </form>
    </div>
</body>
</html>
"""

ENTRY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SANS Index Builder</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma; background: #f4f6f8; padding: 40px; }
        .container { max-width: 900px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 0 15px rgba(0,0,0,0.1); }
        h1, h2 { color: #333; }
        form { margin-bottom: 30px; }
        label { font-weight: bold; }
        input, select, textarea { width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 6px; }
        input, select, textarea { autocomplete: off; }
        button { padding: 10px 20px; background-color: #0057ff; color: white; border: none; border-radius: 6px; cursor: pointer; }
        button:hover { background-color: #0041c4; }
        .entry { background: #f9f9f9; border-left: 4px solid #0057ff; padding: 12px; margin-bottom: 10px; border-radius: 6px; }
        .entry strong { color: #222; }
        .category-header { margin-top: 40px; border-bottom: 2px solid #ddd; padding-bottom: 5px; }
        .export { margin-top: 30px; text-align: right; }
        .export a { color: #0057ff; text-decoration: none; font-weight: bold; margin-left: 10px; }
        .export a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>SANS Index Creator</h1>
        <form method="POST" action="/add">
            <label>Term</label>
            <input name="term" required autocomplete="off">
            <label>Category</label>
            <select name="category">
                <option></option>
                <option>Incident Response</option>
                <option>Windows Process</option>
                <option>Artifacts</option>
                <option>Tools</option>
                <option>Attack Techniques</option>
                <option>Logon/Accounts</option>
                <option>File System</option>
                <option>Credential Theft</option>
                <option>Registry</option>
                <option>Persistence Mechanisms</option>
                <option>Credential Access</option>
                <option>Event Logs</option>
                <option>Memory Analysis</option>
                <option>Commands</option>
                <option>Lateral Movement</option>
            </select>
            <label>Book</label>
            <select name="book">
                {% for i in range(1, settings['books'] + 1) %}
                <option value="{{ i }}" {% if i == settings['last_book'] %}selected{% endif %}>Book {{ i }}</option>
                {% endfor %}
            </select>
            <label>Page Reference</label>
            <input name="page" autocomplete="off">
            <label>Description</label>
            <textarea name="desc" rows="2" autocomplete="off"></textarea>
            <button type="submit">Add Entry</button>
            <div class="export">
                <a href="/export/json">Export JSON</a>
                <a href="/export/pdf" target="_blank">Generate PDF</a>
            </div>
        </form>
        <h2>Index Preview</h2>
        {% for category, items in entries.items() %}
            <div class="category-header"><h3>{{ category }}</h3></div>
            {% for entry in items %}
                <div class="entry">
                    <strong>{{ entry['term'] }}</strong> - Page: {{ entry['page'] }}<br>
                    {{ entry['desc'] }}
                </div>
            {% endfor %}
        {% endfor %}
        
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def home_screen():
    folders = [d for d in os.listdir(ROOT_FOLDER) if os.path.isdir(os.path.join(ROOT_FOLDER, d))]
    return render_template_string(HOME_TEMPLATE, folders=folders)

@app.route("/create", methods=["POST"])
def create_index():
    title = request.form["title"]
    books = int(request.form["books"])
    workbooks = int(request.form["workbooks"])
    folder_path = os.path.join(ROOT_FOLDER, title)
    os.makedirs(folder_path, exist_ok=True)
    settings_data = { "books": books, "workbooks": workbooks, "last_book": 1 }
    with open(os.path.join(folder_path, "settings.json"), "w") as f:
        json.dump(settings_data, f, indent=4)
    with open(os.path.join(folder_path, "data.json"), "w") as f:
        json.dump([], f)
    return redirect(url_for("load_index", folder=title))

@app.route("/load", methods=["POST"])
def load_post():
    return redirect(url_for("load_index", folder=request.form["folder"]))

@app.route("/load/<folder>")
def load_index(folder):
    load_current(folder)
    return redirect(url_for("main_form"))

@app.route("/main", methods=["GET"])
def main_form():
    categorized = defaultdict(list)
    for entry in sorted(index_entries, key=lambda x: (x['category'], x['term'].lower())):
        categorized[entry['category']].append(entry)
    return render_template_string(ENTRY_TEMPLATE, entries=categorized, settings=settings)

@app.route("/add", methods=["POST"])
def add_entry():
    book = int(request.form["book"])
    page_input = request.form["page"]
    full_page = f"{book}:{page_input}" if page_input else f"{book}"
    settings["last_book"] = book
    save_settings()
    index_entries.append({
        "term": request.form["term"],
        "category": request.form["category"],
        "page": full_page,
        "desc": request.form["desc"]
    })
    save_entries()
    return redirect(url_for("main_form"))

@app.route("/export/json")
def export_json():
    return jsonify(index_entries)

@app.route("/export/pdf")
def export_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    term_style = ParagraphStyle(name='Term', fontSize=9, fontName='Helvetica-Bold')
    desc_style = ParagraphStyle(name='Desc', fontSize=8, fontName='Helvetica')
    page_style = ParagraphStyle(name='Page', fontSize=7, fontName='Helvetica-Oblique')
    cat_style = ParagraphStyle(name='Cat', fontSize=10, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=6)
    elements = []
    categorized = defaultdict(list)
    for entry in index_entries:
        categorized[entry['category']].append(entry)
    for category, items in sorted(categorized.items()):
        elements.append(Paragraph(f"{category}", cat_style))
        table_data = [["Term", "Description", "Page"]]
        for item in sorted(items, key=lambda x: x['term'].lower()):
            table_data.append([
                Paragraph(item['term'], term_style),
                Paragraph(item['desc'].replace("\n", "<br/>"), desc_style),
                Paragraph(item['page'], page_style)
            ])
        table = Table(table_data, colWidths=[1.6 * inch, 4.8 * inch, 1 * inch])
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.2 * inch))
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=False, download_name="SANS_Index.pdf", mimetype='application/pdf')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
