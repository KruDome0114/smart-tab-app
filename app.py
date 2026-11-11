from flask import Flask, render_template, request, redirect, url_for, g, Response
import sqlite3
import audio_engine
import os
import time

app = Flask(__name__)
DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tabs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                tab_content TEXT NOT NULL,
                is_public INTEGER DEFAULT 1
            )
        ''')
        try:
            cursor.execute("ALTER TABLE tabs ADD COLUMN audio_file TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        db.commit()

init_db()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
        if cursor.fetchone():
            return render_template('register.html', message="ชื่อนี้มีคนใช้แล้วครับ!")
        else:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, pw))
            db.commit()
            return render_template('login.html', message="สมัครสำเร็จ! ล็อกอินได้เลย")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (user, pw))
        if cursor.fetchone():
            return redirect(url_for('home', username=user))
        else:
            return render_template('login.html', message="ชื่อผู้ใช้ หรือ รหัสผ่านผิดครับ!")
    return render_template('login.html')

@app.route('/home/<username>')
def home(username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, username, title, tab_content FROM tabs ORDER BY id DESC")
    return render_template('home.html', username=username, feed_tabs=cursor.fetchall())

@app.route('/profile/<username>')
def profile(username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, title, tab_content FROM tabs WHERE username = ? ORDER BY id DESC", (username,))
    return render_template('profile.html', username=username, tabs=cursor.fetchall())

@app.route('/studio/<username>')
def studio(username):
    return render_template('studio.html', username=username)

@app.route('/tuner/<username>')
def tuner(username):
    return render_template('tuner.html', username=username)

@app.route('/editor/<username>', methods=['GET', 'POST'])
def editor(username):
    tab_data, audio_file = "", ""
    tab_id = request.args.get('tab_id', '')
    title = request.args.get('title', 'แท็บใหม่ของฉัน')
    if request.method == 'POST':
        tab_data = request.form.get('generated_tab', '')
        audio_file = request.form.get('audio_file', '')
    return render_template('editor.html', username=username, tab_data=tab_data, tab_id=tab_id, title=title, audio_file=audio_file)

@app.route('/help/<username>')
def help_guide(username):
    return render_template('help.html', username=username)

@app.route('/view/<username>/<int:tab_id>')
def view_tab(username, tab_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, username, title, tab_content, audio_file FROM tabs WHERE id = ?", (tab_id,))
    return render_template('view.html', username=username, tab=cursor.fetchone())

@app.route('/edit/<username>/<int:tab_id>')
def edit_tab(username, tab_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, title, tab_content, audio_file FROM tabs WHERE id = ? AND username = ?", (tab_id, username))
    tab = cursor.fetchone()
    if tab:
        return render_template('editor.html', username=username, tab_data=tab[2], tab_id=tab[0], title=tab[1], audio_file=tab[3])
    return redirect(url_for('profile', username=username))

@app.route('/delete/<username>/<int:tab_id>', methods=['POST'])
def delete_tab(username, tab_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM tabs WHERE id = ? AND username = ?", (tab_id, username))
    db.commit()
    return redirect(url_for('profile', username=username))

@app.route('/save_tab', methods=['POST'])
def save_tab():
    username = request.form.get('username')
    title, tab_data = request.form.get('title', 'แท็บใหม่ของฉัน'), request.form.get('tab_data', '')
    tab_id, audio_file = request.form.get('tab_id', ''), request.form.get('audio_file', '')
    db, cursor = get_db(), get_db().cursor()
    if tab_id:
        cursor.execute("UPDATE tabs SET title = ?, tab_content = ?, audio_file = ? WHERE id = ? AND username = ?", (title, tab_data, audio_file, tab_id, username))
    else:
        cursor.execute("INSERT INTO tabs (username, title, tab_content, audio_file) VALUES (?, ?, ?, ?)", (username, title, tab_data, audio_file))
    db.commit()
    return redirect(url_for('profile', username=username))

# ---------------------------------------------------------
# API โฉมใหม่: รับไฟล์เสียงจากหน้าเว็บ มาประมวลผลแท็บ
# ---------------------------------------------------------
@app.route('/api/process_record', methods=['POST'])
def process_record():
    if 'audio' not in request.files:
        return {"status": "error", "message": "ไม่พบไฟล์เสียง"}
        
    file = request.files['audio']
    filename = f"record_{int(time.time())}.wav"
    
    if not os.path.exists('static'):
        os.makedirs('static')
        
    filepath = os.path.join('static', filename)
    file.save(filepath)
    
    # ส่งไฟล์ที่บันทึกเสร็จ ไปให้ AI วิเคราะห์
    tab_text = audio_engine.process_wav_file(filepath)
    
    return {"status": "success", "tab_data": tab_text, "audio_file": filename}

@app.route('/download_tab', methods=['POST'])
def download_tab():
    tab_data = request.form.get('tab_data', 'No tab data found.')
    return Response(tab_data, mimetype="text/plain", headers={"Content-disposition": "attachment; filename=my_smart_tab.txt"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)