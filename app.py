import csv, io, os, secrets, sqlite3
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import quote
from flask import Flask, Response, flash, redirect, render_template, request, session, url_for, jsonify

BASE_DIR=os.path.dirname(os.path.abspath(__file__))
DB_PATH=os.path.join(BASE_DIR,'kings_tourism.db')
app=Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY',secrets.token_hex(32)),ADMIN_USERNAME=os.environ.get('ADMIN_USERNAME','admin'),ADMIN_PASSWORD=os.environ.get('ADMIN_PASSWORD','change-this-password'),WHATSAPP_NUMBER=os.environ.get('WHATSAPP_NUMBER',''))

def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db(); c.executescript("""CREATE TABLE IF NOT EXISTS inquiries(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,trip_type TEXT NOT NULL,starting_location TEXT NOT NULL,destination TEXT NOT NULL,travel_date TEXT NOT NULL,duration TEXT NOT NULL,travellers INTEGER NOT NULL,details TEXT,name TEXT NOT NULL,phone TEXT NOT NULL); CREATE TABLE IF NOT EXISTS visits(id INTEGER PRIMARY KEY AUTOINCREMENT,visited_at TEXT NOT NULL,visitor_token TEXT NOT NULL,path TEXT NOT NULL); CREATE INDEX IF NOT EXISTS idx_visits_token ON visits(visitor_token);"""); c.commit(); c.close()

def admin_required(fn):
    @wraps(fn)
    def wrap(*a,**kw):
        if not session.get('admin_authenticated'): return redirect(url_for('admin_login',next=request.path))
        return fn(*a,**kw)
    return wrap

@app.before_request
def track():
    if request.endpoint in {'static','admin_login','admin_logout'} or request.path.startswith('/admin'): return
    token=request.cookies.get('ktc_visitor') or secrets.token_urlsafe(18)
    c=db(); c.execute('INSERT INTO visits(visited_at,visitor_token,path) VALUES(?,?,?)',(datetime.now(timezone.utc).isoformat(),token,request.path)); c.commit(); c.close()
    if not request.cookies.get('ktc_visitor'): request._new_visitor=token

@app.after_request
def cookie(resp):
    token=getattr(request,'_new_visitor',None)
    if token: resp.set_cookie('ktc_visitor',token,max_age=31536000,httponly=True,samesite='Lax',secure=False)
    return resp

@app.route('/')
def index(): return render_template('index.html')

@app.post('/api/inquiry')
def inquiry():
    f={k:request.form.get(k,'').strip() for k in ['trip_type','starting_location','destination','travel_date','duration','details','name','phone']}
    f['trip_type']=request.form.get('tripType','').strip(); f['starting_location']=request.form.get('startingLocation','').strip(); f['destination']=request.form.get('destination','').strip(); f['travel_date']=request.form.get('travelDate','').strip(); f['duration']=request.form.get('duration','').strip(); f['details']=request.form.get('details','').strip(); f['name']=request.form.get('name','').strip(); f['phone']=request.form.get('phone','').strip()
    try: travellers=int(request.form.get('travellers','0'))
    except ValueError: travellers=0
    if any(not f[k] for k in ['trip_type','starting_location','destination','travel_date','duration','name','phone']) or not 1<=travellers<=50:
        flash('Please fill all required inquiry fields correctly.','error'); return redirect(url_for('index')+'#destinations')
    c=db(); c.execute('INSERT INTO inquiries(created_at,trip_type,starting_location,destination,travel_date,duration,travellers,details,name,phone) VALUES(?,?,?,?,?,?,?,?,?,?)',(datetime.now(timezone.utc).isoformat(),f['trip_type'],f['starting_location'],f['destination'],f['travel_date'],f['duration'],travellers,f['details'],f['name'],f['phone'])); c.commit(); c.close()
    number=''.join(x for x in app.config['WHATSAPP_NUMBER'] if x.isdigit())
    msg=f"Hello Kings Tourism Crest! I'd like to enquire about a trip.\nTrip type: {f['trip_type']}\nStarting location: {f['starting_location']}\nDestination: {f['destination']}\nTravel date: {f['travel_date']}\nDuration: {f['duration']}\nTravellers: {travellers}\nName: {f['name']}\nPhone: {f['phone']}\nDetails: {f['details'] or 'Not specified'}"
    if len(number)>=10:
        return jsonify(ok=True, whatsapp_url=f'https://wa.me/{number}?text={quote(msg)}')
    return jsonify(ok=True, whatsapp_url=None)

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    if session.get('admin_authenticated'): return redirect(url_for('admin_dashboard'))
    if request.method=='POST':
        u=request.form.get('username',''); p=request.form.get('password','')
        if secrets.compare_digest(u,app.config['ADMIN_USERNAME']) and secrets.compare_digest(p,app.config['ADMIN_PASSWORD']):
            session.clear(); session['admin_authenticated']=True; session.permanent=True; return redirect(request.args.get('next') or url_for('admin_dashboard'))
        flash('Invalid admin username or password.','error')
    return render_template('admin_login.html')

@app.get('/admin/logout')
def admin_logout(): session.clear(); return redirect(url_for('admin_login'))

@app.get('/admin')
@admin_required
def admin_dashboard():
    c=db(); total=c.execute('SELECT COUNT(*) FROM visits').fetchone()[0]; unique=c.execute('SELECT COUNT(DISTINCT visitor_token) FROM visits').fetchone()[0]; leads=c.execute('SELECT COUNT(*) FROM inquiries').fetchone()[0]; today=datetime.now(timezone.utc).date().isoformat(); today_visits=c.execute("SELECT COUNT(*) FROM visits WHERE substr(visited_at,1,10)=?",(today,)).fetchone()[0]; inquiries=c.execute('SELECT * FROM inquiries ORDER BY id DESC LIMIT 100').fetchall(); recent=c.execute('SELECT substr(visited_at,1,16) visited_at,path FROM visits ORDER BY id DESC LIMIT 30').fetchall(); c.close()
    return render_template('admin.html',total_visits=total,unique_visitors=unique,inquiries_count=leads,today_visits=today_visits,inquiries=inquiries,recent_visits=recent,whatsapp_number=app.config['WHATSAPP_NUMBER'])

@app.post('/admin/inquiries/<int:iid>/delete')
@admin_required
def delete_inquiry(iid):
    c=db(); c.execute('DELETE FROM inquiries WHERE id=?',(iid,)); c.commit(); c.close(); return redirect(url_for('admin_dashboard'))

@app.get('/admin/export.csv')
@admin_required
def export_csv():
    c=db(); rows=c.execute('SELECT * FROM inquiries ORDER BY id DESC').fetchall(); c.close(); out=io.StringIO(); w=csv.writer(out); w.writerow(['ID','Created','Trip Type','Starting','Destination','Travel Date','Duration','Travellers','Details','Name','Phone']); [w.writerow([r[k] for k in r.keys()]) for r in rows]; return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=kings-tourism-inquiries.csv'})

if __name__=='__main__':
    init_db(); app.run(debug=True,host='127.0.0.1',port=5000)
