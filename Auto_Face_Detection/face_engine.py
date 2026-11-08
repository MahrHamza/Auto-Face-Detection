from pathlib import Path
import cv2, numpy as np
ROOT=Path(__file__).resolve().parent; FACES=ROOT/'faces'; PHOTOS=ROOT/'photos'; MODEL=ROOT/'face_model.yml'
CASCADE_PATH=Path(cv2.data.haarcascades)/'haarcascade_frontalface_default.xml'
CASCADE=cv2.CascadeClassifier(str(CASCADE_PATH))
_recognizer=None; _mtime=None
def ensure_dirs():FACES.mkdir(exist_ok=True); PHOTOS.mkdir(exist_ok=True)
def detect(gray):
 if CASCADE.empty():raise RuntimeError(f'Haar cascade file not found: {CASCADE_PATH}. Reinstall opencv-contrib-python==4.11.0.86')
 return CASCADE.detectMultiScale(cv2.equalizeHist(gray),1.12,5,minSize=(65,65))
def add_photo_sample(pid,image_path):
 ensure_dirs(); im=cv2.imread(str(image_path))
 if im is None:raise ValueError('Selected image could not be opened.')
 gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY); faces=detect(gray)
 if len(faces)==0:raise ValueError('No clear face was detected in this photo. Choose a front-facing, well-lit photo.')
 x,y,w,h=max(faces,key=lambda r:r[2]*r[3]); crop=cv2.resize(gray[y:y+h,x:x+w],(200,200))
 folder=FACES/str(pid); folder.mkdir(exist_ok=True); cv2.imwrite(str(folder/'001.jpg'),crop)
 return True
def add_camera_sample(pid,frame):
 gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); faces=detect(gray)
 if not len(faces):return False
 x,y,w,h=max(faces,key=lambda r:r[2]*r[3]); crop=cv2.resize(gray[y:y+h,x:x+w],(200,200)); folder=FACES/str(pid); folder.mkdir(exist_ok=True)
 n=len(list(folder.glob('*.jpg')))+1; cv2.imwrite(str(folder/f'{n:03}.jpg'),crop); return True
def train():
 global _recognizer,_mtime
 if not hasattr(cv2,'face'):raise RuntimeError('OpenCV contrib is required. Install opencv-contrib-python==4.11.0.86')
 images=[]; labels=[]
 for folder in FACES.iterdir():
  if folder.is_dir() and folder.name.isdigit():
   for f in folder.glob('*.jpg'):
    im=cv2.imread(str(f),cv2.IMREAD_GRAYSCALE)
    if im is not None:images.append(cv2.resize(im,(200,200))); labels.append(int(folder.name))
 if not images:return 0
 model=cv2.face.LBPHFaceRecognizer_create(); model.train(images,np.asarray(labels,dtype=np.int32)); model.save(str(MODEL)); _recognizer=model; _mtime=MODEL.stat().st_mtime; return len(images)
def load_model():
 global _recognizer,_mtime
 if not hasattr(cv2,'face') or not MODEL.exists():return False
 mt=MODEL.stat().st_mtime
 if _recognizer is None or _mtime!=mt:
  _recognizer=cv2.face.LBPHFaceRecognizer_create(); _recognizer.read(str(MODEL)); _mtime=mt
 return True
def recognize(gray_face,threshold=72):
 if not load_model():return None,None
 label,score=_recognizer.predict(cv2.resize(gray_face,(200,200)))
 return (int(label),float(score)) if score<float(threshold) else (None,float(score))
