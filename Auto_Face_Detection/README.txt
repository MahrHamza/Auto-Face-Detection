AUTO FACE DETECTION — SMART ATTENDANCE DESKTOP APP
==================================================

WHAT IS INCLUDED
- Two separate workspaces: User Panel and Admin Panel.
- Admin login protects student management, reports and security settings.
- Admin can register, edit and delete student profiles.
- Required fields: full name, unique Student ID, department and face photo.
- Email is optional.
- Face photo is copied into the local photos folder and enrolled for recognition.
- User Panel scans the webcam and marks attendance for recognized enrolled students.
- Attendance stores local date/time; one check-in per student per day.
- Admin dashboard shows registered, present and not-checked-in counts.
- Searchable attendance history and CSV export.
- Admin password change screen; password stored as salted PBKDF2 hash.
- Animated liquid-glass dark interface and translucent panels.
- Local SQLite database; no cloud upload.

WINDOWS 11 / VS CODE SETUP
1. Extract the ZIP to a writable folder, for example C:\AutoFaceDetection.
2. Open the extracted folder in VS Code.
3. Open Terminal > New Terminal.
4. Create the virtual environment:
      py -3.12 -m venv .venv
5. Activate it:
      .venv\Scripts\activate
6. Install packages:
      python -m pip install --upgrade pip
      python -m pip install -r requirements.txt
7. Run:
      python main.py

FIRST ADMIN LOGIN
Username: admin
Password: admin12345
Change this password immediately after first login from Admin Panel > Security.

HOW TO USE
ADMIN:
1. Choose ADMIN PANEL from the portal.
2. Sign in with the first-run credentials above.
3. Open Student Management.
4. Enter student name, unique Student ID, department and optional email.
5. Browse and choose a clear, front-facing face photo.
6. Click SAVE / UPDATE STUDENT.
7. To edit, select a student row and load it into the form. Change details/photo and save.
8. To delete, select a student row and click DELETE SELECTED.
9. Open Attendance Records to search or export a CSV report.

USER:
1. Return to the portal and open USER PANEL.
2. Click START SCANNING and allow Windows desktop-app camera access.
3. A registered student should face the camera in clear, even lighting.
4. The app requires several consecutive matches before check-in and records one attendance per day.

CAMERA TROUBLESHOOTING
- Windows Settings > Privacy & security > Camera: enable Camera access and desktop-app access.
- Close Windows Camera, Teams, Zoom and browser video calls before starting this app.
- Ensure the webcam works in the Windows Camera app.
- This build currently opens camera index 0. If your webcam is another index, change VideoCapture(0) in main.py to VideoCapture(1).

IMPORTANT FACE-RECOGNITION LIMITATIONS
- A single uploaded photo can enroll a profile, but recognition is more reliable with multiple genuine photos from different angles and lighting. This build's photo upload creates the initial face sample; additional sample-capture workflow can be added if needed.
- Haar detection + LBPH recognition is a basic local prototype, not a certified biometric security system. False matches and missed matches are possible. Test carefully before real attendance use.
- Provide a manual attendance alternative, obtain informed consent, protect the project folder and restrict access to biometric photos/samples.
- Attendance and face images are stored locally in attendance.db, photos/ and faces/.

UPGRADE NOTE
The app upgrades an existing attendance.db by adding Student ID and photo columns. Back up your existing attendance.db and faces/ folder before replacing an older project.
