

# purpose
This project is created for the course database and information systems, as seen in forlæsning 1 i am primarily using python combined with flask and postgresql. I have chosen to opt for using external templates for the calendar creation and such, since the frontend of this application isnt truly relevent to the course.

# for my fellow students

flask --app backend.app run         

is the command to run the application and please dont mess with the internal psql postres.

# Student Collaboration Tool
A Flask-based web application that helps student groups find optimal meeting times and manage project deadlines based on shared availability. Calendar data can be imported via `.ics` files.

---

## Features

- User registration and group membership
- Project creation with deadlines and effort estimation
- Upload `.ics` calendar files to generate availability
- Detect shared free time across group members
- Alert when insufficient time exists to meet project goals

---

##Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/student-collab-tool.git
cd student-collab-tool
