
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import os
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'mikrowisp_secret'

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        service TEXT NOT NULL,
        status TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()

@app.before_first_request
def create_default_user():
    init_db()
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', '1234', 'admin'))
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    query = request.form.get('query', '')
    filter_status = request.args.get('filter', '')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    sql = "SELECT * FROM clients WHERE name LIKE ? OR service LIKE ?"
    args = [f'%{query}%', f'%{query}%']
    if filter_status:
        sql += " AND status = ?"
        args.append(filter_status)
    c.execute(sql, args)
    clients = c.fetchall()
    c.execute("SELECT COUNT(*) FROM clients WHERE status = 'activo'")
    active_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM clients WHERE status = 'suspendido'")
    suspended_count = c.fetchone()[0]
    conn.close()
    return render_template('index.html', clients=clients, active_count=active_count,
                           suspended_count=suspended_count, query=query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            session['role'] = user[3]
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        name = request.form['name']
        service = request.form['service']
        status = request.form['status']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO clients (name, service, status) VALUES (?, ?, ?)', (name, service, status))
        conn.commit()
        conn.close()
        return redirect(url_for('home'))
    return render_template('add_client.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_client(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        service = request.form['service']
        status = request.form['status']
        c.execute('UPDATE clients SET name=?, service=?, status=? WHERE id=?', (name, service, status, id))
        conn.commit()
        conn.close()
        return redirect(url_for('home'))
    c.execute('SELECT * FROM clients WHERE id=?', (id,))
    client = c.fetchone()
    conn.close()
    return render_template('edit_client.html', client=client)

@app.route('/delete/<int:id>')
def delete_client(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM clients WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/export')
def export_csv():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT name, service, status FROM clients')
    clients = c.fetchall()
    conn.close()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Nombre', 'Servicio', 'Estado'])
    cw.writerows(clients)
    output = si.getvalue()
    return send_file(StringIO(output), mimetype='text/csv', download_name='clientes.csv', as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
