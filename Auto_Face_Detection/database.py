import sqlite3, hashlib, secrets
from pathlib import Path
from datetime import datetime, date
DB_PATH=Path(__file__).resolve().with_name('attendance.db')
def connect():
 c=sqlite3.connect(DB_PATH,timeout=20); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init_db():
 with connect() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS people(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,role TEXT DEFAULT 'Student',department TEXT DEFAULT '',email TEXT DEFAULT '',created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT,person_id INTEGER NOT NULL,check_in TEXT NOT NULL,status TEXT DEFAULT 'Present',FOREIGN KEY(person_id) REFERENCES people(id) ON DELETE CASCADE);
  CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,salt TEXT NOT NULL,created_at TEXT NOT NULL);
  ''')
  cols={r['name'] for r in c.execute('PRAGMA table_info(people)')}
  for name,typ in [('student_id','TEXT'),('photo_path','TEXT')]:
   if name not in cols: c.execute(f'ALTER TABLE people ADD COLUMN {name} {typ}')
  c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_people_student_id ON people(student_id) WHERE student_id IS NOT NULL AND student_id <> ""')
  c.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(check_in)')
  if not c.execute('SELECT 1 FROM admins LIMIT 1').fetchone():
   salt=secrets.token_hex(16); digest=hashlib.pbkdf2_hmac('sha256',b'admin12345',salt.encode(),240000).hex()
   c.execute('INSERT INTO admins(username,password_hash,salt,created_at) VALUES(?,?,?,?)',('admin',digest,salt,datetime.now().isoformat(timespec='seconds')))
def verify_admin(username,password):
 with connect() as c: row=c.execute('SELECT * FROM admins WHERE username=?',(username.strip(),)).fetchone()
 if not row:return False
 test=hashlib.pbkdf2_hmac('sha256',password.encode(),row['salt'].encode(),240000).hex()
 return secrets.compare_digest(test,row['password_hash'])
def change_password(username,old,new):
 if not verify_admin(username,old):return False
 salt=secrets.token_hex(16); digest=hashlib.pbkdf2_hmac('sha256',new.encode(),salt.encode(),240000).hex()
 with connect() as c:c.execute('UPDATE admins SET password_hash=?,salt=? WHERE username=?',(digest,salt,username))
 return True
def save_person(name,student_id,department,email,photo_path,pid=None):
 with connect() as c:
  if pid:
   c.execute('UPDATE people SET name=?,student_id=?,department=?,email=?,photo_path=? WHERE id=?',(name,student_id,department,email,photo_path,pid)); return pid
  cur=c.execute('INSERT INTO people(name,role,department,email,created_at,student_id,photo_path) VALUES(?,?,?,?,?,?,?)',(name,'Student',department,email,datetime.now().isoformat(timespec='seconds'),student_id,photo_path)); return cur.lastrowid
def people():
 with connect() as c:return c.execute('SELECT * FROM people ORDER BY name').fetchall()
def person(pid):
 with connect() as c:return c.execute('SELECT * FROM people WHERE id=?',(pid,)).fetchone()
def find_student(student_id):
 with connect() as c:return c.execute('SELECT * FROM people WHERE student_id=?',(student_id,)).fetchone()
def delete_person(pid):
 with connect() as c:c.execute('DELETE FROM attendance WHERE person_id=?',(pid,)); c.execute('DELETE FROM people WHERE id=?',(pid,))
def mark_attendance(pid):
 stamp=datetime.now().isoformat(timespec='seconds'); today=date.today().isoformat()
 with connect() as c:
  cur=c.execute('INSERT OR IGNORE INTO attendance(person_id,check_in,status) SELECT ?,?,\'Present\' WHERE NOT EXISTS(SELECT 1 FROM attendance WHERE person_id=? AND date(check_in)=?)',(pid,stamp,pid,today))
  return cur.rowcount==1,stamp
def attendance_rows(query=''):
 sql='SELECT a.id,p.name,p.student_id,p.department,a.check_in,a.status FROM attendance a JOIN people p ON p.id=a.person_id'; args=[]
 if query:sql+=' WHERE p.name LIKE ? OR p.student_id LIKE ? OR p.department LIKE ?'; args=[f'%{query}%']*3
 sql+=' ORDER BY a.check_in DESC'
 with connect() as c:return c.execute(sql,args).fetchall()
def stats():
 with connect() as c:
  total=c.execute('SELECT COUNT(*) FROM people').fetchone()[0]; present=c.execute('SELECT COUNT(DISTINCT person_id) FROM attendance WHERE date(check_in)=?',(date.today().isoformat(),)).fetchone()[0]
 return total,present,max(0,total-present)
