## Future Works

CheckMe was designed with extensibility in mind. The following features and
directions are planned or proposed for future development:

### 🖥️ Web or Desktop Application
A web-based or desktop version of the teacher portal would allow teachers to manage
assessments, view scores, and export results directly from a browser or desktop
computer — without needing a phone. This would be particularly useful in school
computer labs or for teachers who prefer a larger screen for data review.

### 🖨️ PC-Based Scanning (No Raspberry Pi Required)
The current system requires a Raspberry Pi as the scanning station. A future version
could replace the Raspberry Pi entirely with a desktop or laptop application that
communicates directly with a USB-connected scanner. Since most school computers
already have scanner software installed, this would dramatically lower the hardware
cost and setup complexity. Any PC with a compatible scanner could become a checking
station.

### 👨‍💼 Admin Portal
An admin panel for school administrators to oversee all teacher accounts, subjects,
sections, and assessment activity across the institution — providing a school-wide
view of assessment data without requiring access to individual teacher accounts.

### 📊 Analytics Dashboard
Visual analytics for teachers showing class performance trends across assessments —
including score distributions, question-level difficulty analysis, and student
progress over time.

### 🔔 Push Notifications
Real-time push notifications to notify teachers when a student's answer sheet has
been successfully scanned and scored, or when a student requests enrollment in their
subject.

### 🌐 Broader Scanner Compatibility Testing
CheckMe has been confirmed working on the **Epson L3210 Series** and
**Canon PIXMA MG2570S**. Future work includes formal testing across a wider range
of flatbed scanner models to build a verified compatibility list.

### 📱 Student Mobile Improvements
Enhanced student-facing features such as score history graphs, notifications when
results are published, and the ability to view scanned answer sheet images alongside
their personal breakdown.