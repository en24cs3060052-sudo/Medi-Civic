# Medi-Civic 🛡️

**Student Grievance Reporting & Priority-Management System**

A web-based platform that allows students to submit institutional complaints and organizes them by urgency and importance for efficient resolution by authorities.

## Features

- **Student Portal**: Submit complaints, track status, view resolution updates
- **Authority Dashboard**: View all complaints sorted by priority, update statuses
- **Priority Engine**: Automatic priority scoring (Critical / High / Medium / Low) based on urgency × importance
- **Category System**: 9 categories — Infrastructure, Sanitation, Academic, Safety, Hostel, Transportation, Administrative, IT & Network, Other
- **Analytics Dashboard**: Visual breakdown by category, priority level, and status
- **Activity Timeline**: Track every status change with comments

## Tech Stack

| Component      | Technology           |
|----------------|----------------------|
| Frontend       | HTML, CSS, JavaScript, Bootstrap 5 |
| Backend        | Python Flask         |
| Database       | SQLite               |
| Styling        | Custom CSS + Bootstrap Icons |

## Quick Start

1. **Install Python** (3.8+) and pip

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open in browser:** http://127.0.0.1:5000

## Demo Accounts

| Role      | Username   | Password    |
|-----------|------------|-------------|
| Student   | student1   | student123  |
| Authority | authority  | auth123     |
| Admin     | admin      | admin123    |

## Priority Calculation

Priority is calculated using: `score = 0.6 × urgency + 0.4 × importance`

| Score Range | Level    |
|-------------|----------|
| 4.0 – 5.0  | Critical |
| 3.0 – 3.99 | High     |
| 2.0 – 2.99 | Medium   |
| 1.0 – 1.99 | Low      |

## Project Structure

```
medi-civic/
├── app.py                  # Flask application (backend)
├── requirements.txt        # Python dependencies
├── medi_civic.db           # SQLite database (auto-created)
├── static/
│   └── css/
│       └── style.css       # Custom stylesheet
└── templates/
    ├── base.html           # Base layout template
    ├── index.html           # Landing page
    ├── login.html           # Login page
    ├── register.html        # Registration page
    ├── dashboard.html       # Student/Authority dashboard
    ├── new_complaint.html   # New complaint form
    ├── view_complaint.html  # Complaint detail view
    └── analytics.html       # Analytics dashboard
```

## License

Academic project — for educational purposes.
