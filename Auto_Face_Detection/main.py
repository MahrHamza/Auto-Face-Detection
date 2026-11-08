import sys, os, shutil, csv, uuid
from pathlib import Path
from datetime import datetime
import cv2
from PySide6.QtCore import Qt,QTimer,QRectF
from PySide6.QtGui import QColor,QPainter,QLinearGradient,QRadialGradient,QImage,QPixmap
from PySide6.QtWidgets import *
import database as db
import face_engine as fe

APP='AUTO FACE DETECTION | SMART ATTENDANCE'
ROOT=Path(__file__).resolve().parent
STYLE=r'''
*{font-family:'Segoe UI';color:#eaf5ff;font-size:13px} QMainWindow{background:transparent} QWidget{background:transparent}
QFrame#Glass,QFrame#Panel,QFrame#Top{background:rgba(9,30,54,218);border:1px solid rgba(111,196,255,85);border-radius:20px}
QFrame#Panel{background:rgba(5,22,42,225)} QFrame#Top{background:rgba(14,43,72,205)}
QLabel#Brand{font-size:27px;font-weight:900;color:#f4fbff;letter-spacing:2px} QLabel#Kicker{font-size:10px;font-weight:800;letter-spacing:2px;color:#6ee6ff}
QLabel#Heading{font-size:30px;font-weight:800;color:#f5fbff} QLabel#Sub{font-size:13px;color:#9dbbd5} QLabel#Metric{font-size:34px;font-weight:900;color:#70e5ff}
QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(16,126,219,235),stop:1 rgba(0,185,199,220));border:1px solid rgba(122,226,255,130);border-radius:12px;padding:12px 17px;font-weight:750;color:white}
QPushButton:hover{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #199be9,stop:1 #16c9d0);border:1px solid #a5f4ff} QPushButton:pressed{padding-top:14px}
QPushButton#Secondary{background:rgba(24,64,99,205);border:1px solid rgba(111,177,220,90)} QPushButton#Danger{background:rgba(151,43,67,220);border:1px solid rgba(255,120,145,120)}
QLineEdit,QComboBox,QSpinBox{background:rgba(2,14,29,205);border:1px solid rgba(100,174,224,115);border-radius:10px;padding:12px;color:#f3faff;selection-background-color:#128ec9}
QTableWidget{background:rgba(2,14,29,180);alternate-background-color:rgba(28,65,94,125);border:1px solid rgba(111,177,225,75);border-radius:12px;gridline-color:rgba(120,170,210,35)}
QHeaderView::section{background:rgba(18,67,105,240);color:#b8efff;padding:11px;border:0;font-weight:800} QScrollArea{border:0;background:transparent}
QScrollBar:vertical{background:rgba(3,16,32,100);width:10px;margin:2px;border-radius:5px} QScrollBar::handle:vertical{background:rgba(78,173,226,180);min-height:30px;border-radius:5px}
'''
class AnimatedBackdrop(QWidget):
 def __init__(self):
  super().__init__();self.phase=0;self.t=QTimer(self);self.t.timeout.connect(self.tick);self.t.start(40)
 def tick(self):self.phase+=1;self.update()
 def paintEvent(self,e):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=self.rect();g=QLinearGradient(0,0,r.width(),r.height());g.setColorAt(0,QColor('#030b18'));g.setColorAt(.5,QColor('#0a2545'));g.setColorAt(1,QColor('#041323'));p.fillRect(r,g)
  import math
  for i,(x,y,rad,col) in enumerate([(0.15,.2,260,(0,145,255,55)),(.8,.25,300,(0,220,220,42)),(.48,.9,340,(65,80,255,38))]):
   xx=r.width()*(x+.035*math.sin(self.phase/55+i)); yy=r.height()*(y+.04*math.cos(self.phase/70+i)); c=QColor(*col); z=QColor(*col);z.setAlpha(0);rg=QRadialGradient(xx,yy,rad);rg.setColorAt(0,c);rg.setColorAt(1,z);p.setPen(Qt.NoPen);p.setBrush(rg);p.drawEllipse(QRectF(xx-rad,yy-rad,rad*2,rad*2))
  p.end()
def panel():
 f=QFrame();f.setObjectName('Glass');return f
def label(text,obj=None):
 w=QLabel(text);w.setWordWrap(True)
 if obj:w.setObjectName(obj)
 return w
def table(headers):
 t=QTableWidget(0,len(headers));t.setHorizontalHeaderLabels(headers);t.setAlternatingRowColors(True);t.setEditTriggers(QAbstractItemView.NoEditTriggers);t.setSelectionBehavior(QAbstractItemView.SelectRows);t.setSelectionMode(QAbstractItemView.SingleSelection);t.verticalHeader().hide();t.horizontalHeader().setStretchLastSection(True);t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);return t
class MainWindow(QMainWindow):
 def __init__(self):
  super().__init__();db.init_db();fe.ensure_dirs();self.setWindowTitle(APP);self.resize(1480,940);self.setMinimumSize(1050,700)
  self.cap=None;self.frame=None;self.admin_user='admin';self.edit_id=None;self.streak={};self.cooldown={}
  self.bg=AnimatedBackdrop();self.setCentralWidget(self.bg);outer=QVBoxLayout(self.bg);outer.setContentsMargins(18,18,18,18)
  self.stack=QStackedWidget();outer.addWidget(self.stack)
  self.build_home();self.stack.addWidget(self.home)
  self.build_user();self.stack.addWidget(self.user)
  self.build_login();self.stack.addWidget(self.login)
  self.build_admin();self.stack.addWidget(self.admin);self.stack.setCurrentWidget(self.home)
  self.timer=QTimer(self);self.timer.timeout.connect(self.camera_tick);self.clock_timer=QTimer(self);self.clock_timer.timeout.connect(self.update_clock);self.clock_timer.start(1000);self.update_clock()
 def update_clock(self):
  if hasattr(self,'clock'):self.clock.setText(datetime.now().strftime('%a, %d %b %Y  |  %I:%M:%S %p'))
 def shell(self,title,desc):
  w=QWidget();v=QVBoxLayout(w);v.setContentsMargins(12,10,12,12);v.setSpacing(15);top=QFrame();top.setObjectName('Top');h=QHBoxLayout(top);h.addWidget(label('AUTO FACE DETECTION','Brand'));h.addStretch();self.clock=label('','Sub');h.addWidget(self.clock);v.addWidget(top);v.addWidget(label(title,'Heading'));v.addWidget(label(desc,'Sub'));return w,v
 def build_home(self):
  self.home,v=self.shell('SMART ATTENDANCE PORTAL','Choose your workspace. User check-in is camera based; administration is protected by a password.')
  row=QHBoxLayout();
  for title,desc,btn,slot,ic in [('USER PANEL','Automatic face scan and instant attendance check-in. No admin access.','OPEN USER PANEL',self.show_user,'◉'),('ADMIN PANEL','Secure administrator login, student profiles, records and settings.','ADMIN LOGIN',self.show_login,'⌘')]:
   f=panel();f.setMinimumHeight(300);z=QVBoxLayout(f);z.setContentsMargins(28,28,28,28);z.addWidget(label(ic,'Metric'));z.addWidget(label(title,'Kicker'));z.addWidget(label(desc,'Heading'));z.addStretch();b=QPushButton(btn);b.clicked.connect(slot);z.addWidget(b);row.addWidget(f)
  v.addLayout(row);v.addStretch();v.addWidget(label('LOCAL-FIRST • SQLITE DATABASE • FACE DETECTION • ATTENDANCE TIMESTAMP','Kicker'))
 def build_user(self):
  self.user,v=self.shell('USER CHECK-IN','Stand in front of the camera. A registered face is matched and attendance is saved with the exact local date and time.')
  row=QHBoxLayout();f=panel();a=QVBoxLayout(f);self.user_view=label('CAMERA STANDBY\nPress START SCANNING');self.user_view.setAlignment(Qt.AlignCenter);self.user_view.setMinimumSize(640,440);self.user_view.setStyleSheet('background:rgba(0,5,14,190);border:1px solid #347ba6;border-radius:16px;color:#83c6e9;font-size:18px;font-weight:800');a.addWidget(self.user_view)
  buttons=QHBoxLayout();b=QPushButton('▶ START SCANNING');b.clicked.connect(self.start_camera);stop=QPushButton('■ STOP');stop.setObjectName('Secondary');stop.clicked.connect(self.stop_camera);buttons.addWidget(b);buttons.addWidget(stop);a.addLayout(buttons);row.addWidget(f,3)
  info=panel();q=QVBoxLayout(info);q.setContentsMargins(24,24,24,24);q.addWidget(label('ATTENDANCE STATUS','Kicker'));self.user_status=label('READY','Metric');q.addWidget(self.user_status);self.user_person=label('No face recognized yet.','Heading');q.addWidget(self.user_person);self.user_time=label('Check-in time will appear here.','Sub');q.addWidget(self.user_time);q.addStretch();q.addWidget(label('• One attendance record per student per day\n• Unknown faces are not registered\n• Please face the camera in good lighting\n• Ask an administrator if your profile is missing','Sub'));back=QPushButton('← BACK TO PORTAL');back.setObjectName('Secondary');back.clicked.connect(self.go_home);q.addWidget(back);row.addWidget(info,2);v.addLayout(row)
 def build_login(self):
  self.login,v=self.shell('ADMINISTRATOR AUTHENTICATION','Only authorized administrators can access student data and attendance management.')
  v.addStretch();f=panel();f.setMaximumWidth(560);f.setMinimumWidth(450);z=QVBoxLayout(f);z.setContentsMargins(34,34,34,34);z.addWidget(label('SECURE SIGN IN','Kicker'));z.addWidget(label('Welcome back','Heading'));z.addWidget(label('Username','Sub'));self.login_user=QLineEdit('admin');z.addWidget(self.login_user);z.addWidget(label('Password','Sub'));self.login_pass=QLineEdit();self.login_pass.setEchoMode(QLineEdit.Password);self.login_pass.returnPressed.connect(self.authenticate);z.addWidget(self.login_pass);self.login_error=label('','Sub');z.addWidget(self.login_error);b=QPushButton('UNLOCK ADMIN WORKSPACE');b.clicked.connect(self.authenticate);z.addWidget(b);home=QPushButton('← Back to portal');home.setObjectName('Secondary');home.clicked.connect(self.go_home);z.addWidget(home);v.addWidget(f,0,Qt.AlignHCenter);v.addStretch()
 def build_admin(self):
  self.admin=QWidget();outer=QVBoxLayout(self.admin);outer.setContentsMargins(0,0,0,0);top=QFrame();top.setObjectName('Top');h=QHBoxLayout(top);h.addWidget(label('AUTO FACE DETECTION  /  ADMIN','Brand'));h.addStretch();h.addWidget(label('ADMINISTRATOR','Kicker'));logout=QPushButton('LOG OUT');logout.setObjectName('Danger');logout.clicked.connect(self.logout);h.addWidget(logout);outer.addWidget(top)
  body=QHBoxLayout();outer.addLayout(body,1);side=QFrame();side.setObjectName('Panel');side.setFixedWidth(220);s=QVBoxLayout(side);s.addWidget(label('CONTROL CENTER','Kicker'))
  self.admin_stack=QStackedWidget();self.admin_pages={}
  for name,builder in [('Overview',self.admin_overview),('Student Management',self.admin_students),('Attendance Records',self.admin_records),('Security',self.admin_security)]:
   b=QPushButton(name);b.setObjectName('Secondary');b.clicked.connect(lambda checked=False,n=name:self.admin_navigate(n));s.addWidget(b)
  s.addStretch();s.addWidget(label('ENCRYPTED PASSWORD HASH\nLOCAL DATABASE','Sub'));body.addWidget(side);body.addWidget(self.admin_stack,1)
  self.admin_pages['Overview']=self.page(self.admin_stack,self.admin_overview);self.admin_pages['Student Management']=self.page(self.admin_stack,self.admin_students);self.admin_pages['Attendance Records']=self.page(self.admin_stack,self.admin_records);self.admin_pages['Security']=self.page(self.admin_stack,self.admin_security);self.admin_navigate('Overview')
 def page(self,stack,builder):
  scroll=QScrollArea();scroll.setWidgetResizable(True);content=QWidget();v=QVBoxLayout(content);v.setContentsMargins(12,12,12,18);v.setSpacing(15);builder(v);v.addStretch();scroll.setWidget(content);stack.addWidget(scroll);return scroll
 def admin_navigate(self,name):
  self.admin_stack.setCurrentWidget(self.admin_pages[name]);
  if name=='Overview':self.refresh_overview()
  if name=='Student Management':self.refresh_students()
  if name=='Attendance Records':self.refresh_records()
 def admin_overview(self,v):
  v.addWidget(label('ADMIN DASHBOARD','Heading'));row=QHBoxLayout();self.metrics=[]
  for t in ['REGISTERED STUDENTS','PRESENT TODAY','NOT CHECKED IN']:
   f=panel();z=QVBoxLayout(f);z.addWidget(label(t,'Kicker'));n=label('0','Metric');z.addWidget(n);self.metrics.append(n);row.addWidget(f)
  v.addLayout(row);v.addWidget(label('RECENT ATTENDANCE','Kicker'));self.recent=table(['Student','Student ID','Department','Check-in time']);self.recent.setMinimumHeight(350);v.addWidget(self.recent);b=QPushButton('＋ ADD NEW STUDENT');b.clicked.connect(lambda:self.admin_navigate('Student Management'));v.addWidget(b)
 def refresh_overview(self):
  total,present,absent=db.stats()
  for w,n in zip(self.metrics,[total,present,absent]):w.setText(str(n))
  rows=db.attendance_rows()[:12];self.recent.setRowCount(len(rows))
  for i,r in enumerate(rows):
   for j,val in enumerate([r['name'],r['student_id'] or '',r['department'],r['check_in'].replace('T',' ')]):self.recent.setItem(i,j,QTableWidgetItem(str(val)))
 def admin_students(self,v):
  v.addWidget(label('STUDENT PROFILE MANAGEMENT','Heading'));f=panel();form=QFormLayout(f);form.setContentsMargins(20,20,20,20);self.f_name=QLineEdit();self.f_sid=QLineEdit();self.f_dept=QLineEdit();self.f_email=QLineEdit();self.photo_path=QLineEdit();self.photo_path.setReadOnly(True)
  form.addRow('Student full name *',self.f_name);form.addRow('Student ID *',self.f_sid);form.addRow('Department *',self.f_dept);form.addRow('Email (optional)',self.f_email)
  photo=QWidget();ph=QHBoxLayout(photo);ph.setContentsMargins(0,0,0,0);ph.addWidget(self.photo_path);pick=QPushButton('BROWSE PHOTO');pick.clicked.connect(self.pick_photo);ph.addWidget(pick);form.addRow('Face photo *',photo)
  self.photo_preview=QLabel('PHOTO PREVIEW');self.photo_preview.setAlignment(Qt.AlignCenter);self.photo_preview.setFixedSize(140,140);self.photo_preview.setStyleSheet('background:rgba(0,0,0,100);border:1px dashed #55a9d4;border-radius:12px');form.addRow('Preview',self.photo_preview)
  actions=QHBoxLayout();save=QPushButton('SAVE / UPDATE STUDENT');save.clicked.connect(self.save_student);clear=QPushButton('CLEAR FORM');clear.setObjectName('Secondary');clear.clicked.connect(self.clear_form);actions.addWidget(save);actions.addWidget(clear);form.addRow(actions);v.addWidget(f)
  bar=QHBoxLayout();self.student_search=QLineEdit();self.student_search.setPlaceholderText('Search name, student ID or department');self.student_search.textChanged.connect(self.refresh_students);bar.addWidget(self.student_search);v.addLayout(bar)
  self.students_table=table(['ID','Student Name','Student ID','Department','Email','Photo']);self.students_table.setMinimumHeight(330);self.students_table.itemSelectionChanged.connect(self.load_selected_student);v.addWidget(self.students_table)
  buttons=QHBoxLayout();edit=QPushButton('LOAD SELECTED FOR EDIT');edit.setObjectName('Secondary');edit.clicked.connect(self.load_selected_student);delete=QPushButton('DELETE SELECTED');delete.setObjectName('Danger');delete.clicked.connect(self.delete_selected);buttons.addWidget(edit);buttons.addWidget(delete);v.addLayout(buttons);self.clear_form()
 def pick_photo(self):
  path,_=QFileDialog.getOpenFileName(self,'Choose student face photo','','Images (*.png *.jpg *.jpeg *.bmp)')
  if path:
   self.photo_path.setText(path);pix=QPixmap(path);self.photo_preview.setPixmap(pix.scaled(130,130,Qt.KeepAspectRatio,Qt.SmoothTransformation))
 def clear_form(self):
  self.edit_id=None
  for w in [self.f_name,self.f_sid,self.f_dept,self.f_email,self.photo_path]:w.clear()
  self.photo_preview.clear();self.photo_preview.setText('PHOTO PREVIEW')
 def save_student(self):
  name=self.f_name.text().strip();sid=self.f_sid.text().strip();dept=self.f_dept.text().strip();email=self.f_email.text().strip();src=self.photo_path.text().strip()
  if not all([name,sid,dept]):QMessageBox.warning(self,'Required fields','Name, Student ID and Department are required.');return
  old=db.person(self.edit_id) if self.edit_id else None
  if not src and not old:QMessageBox.warning(self,'Photo required','Please select a clear face photo.');return
  try:
   same_photo=bool(src and old and old['photo_path'] and Path(src).resolve()==Path(old['photo_path']).resolve())
   new_photo=bool(src and not same_photo)
   if new_photo:
    raw=cv2.imread(src)
    if raw is None:raise ValueError('Selected photo could not be opened.')
    if len(fe.detect(cv2.cvtColor(raw,cv2.COLOR_BGR2GRAY)))==0:raise ValueError('No clear face was detected. Choose a front-facing, well-lit photo.')
    temp=ROOT/'photos'/f'{uuid.uuid4().hex}_{Path(src).name}';shutil.copy2(src,temp);photo=str(temp)
   elif old:photo=old['photo_path']
   else:raise ValueError('Please select a face photo.')
   # Unique Student ID is checked before changing the record.
   match=db.find_student(sid)
   if match and match['id']!=self.edit_id:raise ValueError('This Student ID is already registered.')
   if self.edit_id:
    pid=self.edit_id
    with db.connect() as c:c.execute('UPDATE people SET name=?,student_id=?,department=?,email=?,photo_path=? WHERE id=?',(name,sid,dept,email,photo,pid))
   else:pid=db.save_person(name,sid,dept,email,photo)
   if new_photo:fe.add_photo_sample(pid,photo)
   trained=fe.train() if new_photo else (len(list((fe.FACES/str(pid)).glob('*.jpg'))) if (fe.FACES/str(pid)).exists() else 0)
   QMessageBox.information(self,'Student saved',f'{name} was registered/updated successfully.\nFace model samples: {trained}\n\nTip: add a second or third photo sample later for better recognition.')
   self.clear_form();self.refresh_students();self.refresh_overview()
  except Exception as e:QMessageBox.critical(self,'Could not save student',str(e))
 def refresh_students(self):
  if not hasattr(self,'students_table'):return
  q=self.student_search.text().lower() if hasattr(self,'student_search') else '';rows=[r for r in db.people() if q in ' '.join(str(r[k] or '') for k in ['name','student_id','department','email']).lower()];self.students_table.setRowCount(len(rows))
  for i,r in enumerate(rows):
   for j,val in enumerate([r['id'],r['name'],r['student_id'] or '',r['department'],r['email'] or '', 'Yes' if r['photo_path'] else 'No']):self.students_table.setItem(i,j,QTableWidgetItem(str(val)))
 def selected_id(self):
  rows=self.students_table.selectionModel().selectedRows() if hasattr(self,'students_table') else []
  return int(self.students_table.item(rows[0].row(),0).text()) if rows else None
 def load_selected_student(self):
  pid=self.selected_id()
  if not pid:return
  r=db.person(pid);self.edit_id=pid;self.f_name.setText(r['name']);self.f_sid.setText(r['student_id'] or '');self.f_dept.setText(r['department'] or '');self.f_email.setText(r['email'] or '');self.photo_path.setText(r['photo_path'] or '')
  if r['photo_path'] and Path(r['photo_path']).exists():self.photo_preview.setPixmap(QPixmap(r['photo_path']).scaled(130,130,Qt.KeepAspectRatio,Qt.SmoothTransformation))
 def delete_selected(self):
  pid=self.selected_id()
  if not pid:QMessageBox.warning(self,'Select student','Select a student row first.');return
  r=db.person(pid);ans=QMessageBox.question(self,'Confirm deletion',f'Delete {r["name"]} ({r["student_id"]}) and their attendance records?')
  if ans==QMessageBox.Yes:
   db.delete_person(pid);folder=fe.FACES/str(pid);shutil.rmtree(folder,ignore_errors=True);fe.train();self.clear_form();self.refresh_students();self.refresh_overview()
 def admin_records(self,v):
  v.addWidget(label('ATTENDANCE HISTORY','Heading'));bar=QHBoxLayout();self.record_search=QLineEdit();self.record_search.setPlaceholderText('Search student, ID or department');self.record_search.textChanged.connect(self.refresh_records);bar.addWidget(self.record_search);export=QPushButton('EXPORT CSV');export.clicked.connect(self.export_csv);bar.addWidget(export);v.addLayout(bar);self.records=table(['Student','Student ID','Department','Date & exact check-in time','Status']);self.records.setMinimumHeight(500);v.addWidget(self.records)
 def refresh_records(self):
  if not hasattr(self,'records'):return
  rows=db.attendance_rows(self.record_search.text());self.records.setRowCount(len(rows))
  for i,r in enumerate(rows):
   for j,val in enumerate([r['name'],r['student_id'] or '',r['department'],r['check_in'].replace('T',' '),r['status']]):self.records.setItem(i,j,QTableWidgetItem(str(val)))
 def export_csv(self):
  path,_=QFileDialog.getSaveFileName(self,'Export attendance','attendance_report.csv','CSV (*.csv)')
  if not path:return
  rows=db.attendance_rows(self.record_search.text())
  with open(path,'w',newline='',encoding='utf-8-sig') as f:
   w=csv.writer(f);w.writerow(['Student','Student ID','Department','Check-in','Status']);w.writerows([[r['name'],r['student_id'],r['department'],r['check_in'],r['status']] for r in rows])
  QMessageBox.information(self,'Export complete',f'Report saved to:\n{path}')
 def admin_security(self,v):
  v.addWidget(label('ADMIN SECURITY','Heading'));f=panel();z=QFormLayout(f);z.setContentsMargins(24,24,24,24);self.old_pw=QLineEdit();self.old_pw.setEchoMode(QLineEdit.Password);self.new_pw=QLineEdit();self.new_pw.setEchoMode(QLineEdit.Password);self.confirm_pw=QLineEdit();self.confirm_pw.setEchoMode(QLineEdit.Password);z.addRow('Current password',self.old_pw);z.addRow('New password (8+ chars)',self.new_pw);z.addRow('Confirm new password',self.confirm_pw);b=QPushButton('UPDATE ADMIN PASSWORD');b.clicked.connect(self.change_admin_password);z.addRow(b);v.addWidget(f);v.addWidget(label('First-run credentials are admin / admin12345. Change this password immediately after your first login.','Sub'))
 def change_admin_password(self):
  old=self.old_pw.text();new=self.new_pw.text()
  if len(new)<8 or new!=self.confirm_pw.text():QMessageBox.warning(self,'Invalid password','New password must be at least 8 characters and both new-password fields must match.');return
  if db.change_password(self.admin_user,old,new):QMessageBox.information(self,'Updated','Admin password changed.');self.old_pw.clear();self.new_pw.clear();self.confirm_pw.clear()
  else:QMessageBox.warning(self,'Incorrect password','Current password is incorrect.')
 def authenticate(self):
  u=self.login_user.text().strip();p=self.login_pass.text()
  if db.verify_admin(u,p):self.admin_user=u;self.login_pass.clear();self.admin_navigate('Overview');self.stack.setCurrentWidget(self.admin)
  else:self.login_error.setText('Incorrect username or password.')
 def logout(self):self.stop_camera();self.stack.setCurrentWidget(self.home)
 def show_user(self):self.stack.setCurrentWidget(self.user);self.user_status.setText('READY');self.user_person.setText('No face recognized yet.')
 def show_login(self):self.login_error.clear();self.stack.setCurrentWidget(self.login)
 def go_home(self):self.stop_camera();self.stack.setCurrentWidget(self.home)
 def start_camera(self):
  if self.cap:return
  errors=[]
  for backend in [cv2.CAP_DSHOW,cv2.CAP_MSMF,cv2.CAP_ANY]:
   cap=cv2.VideoCapture(0,backend)
   if cap.isOpened():
    ok,frame=cap.read()
    if ok and frame is not None:self.cap=cap;self.frame=frame;break
   cap.release();errors.append(str(backend))
  if not self.cap:QMessageBox.warning(self,'Camera unavailable','Could not read a frame from camera 0. Close other camera apps and enable Windows desktop-app camera access.');return
  self.timer.start(40);self.user_status.setText('SCANNING…')
 def stop_camera(self):
  self.timer.stop()
  if self.cap:self.cap.release();self.cap=None
  if hasattr(self,'user_view'):self.user_view.setText('CAMERA STOPPED')
 def camera_tick(self):
  if not self.cap:return
  ok,frame=self.cap.read()
  if not ok:return
  self.frame=frame.copy();gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
  try:faces=fe.detect(gray)
  except Exception as e:self.user_status.setText('MODEL ERROR');self.user_person.setText(str(e));faces=[]
  for x,y,w,h in faces:
   crop=cv2.resize(gray[y:y+h,x:x+w],(200,200));pid,score=fe.recognize(crop,65);name='UNKNOWN';color=(20,140,255)
   if pid:
    person=db.person(pid)
    if person:
     name=person['name'];color=(65,230,170);self.streak[pid]=self.streak.get(pid,0)+1
     if self.streak[pid]>=3 and datetime.now().timestamp()-self.cooldown.get(pid,0)>8:
      added,stamp=db.mark_attendance(pid);self.cooldown[pid]=datetime.now().timestamp()
      self.user_status.setText('ATTENDANCE MARKED' if added else 'ALREADY MARKED TODAY');self.user_person.setText(f'{name}  •  {person["student_id"]}');self.user_time.setText(datetime.fromisoformat(stamp).strftime('%A, %d %B %Y  |  %I:%M:%S %p') if added else 'Attendance was already recorded today.')
   else:
    for key in list(self.streak):self.streak[key]=0
   cv2.rectangle(frame,(x,y),(x+w,y+h),color,2);cv2.putText(frame,name,(x,max(25,y-10)),cv2.FONT_HERSHEY_SIMPLEX,.65,color,2)
  if not len(faces):self.user_status.setText('SCANNING FOR FACE…')
  rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB);h,w,ch=rgb.shape;q=QImage(rgb.data,w,h,ch*w,QImage.Format_RGB888).copy();self.user_view.setPixmap(QPixmap.fromImage(q).scaled(self.user_view.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
 def closeEvent(self,e):self.stop_camera();e.accept()
def main():
 app=QApplication(sys.argv);app.setApplicationName(APP);app.setStyle('Fusion');app.setStyleSheet(STYLE);w=MainWindow();w.show();sys.exit(app.exec())
if __name__=='__main__':main()
