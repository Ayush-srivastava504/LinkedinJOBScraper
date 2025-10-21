# JobIntellect - LinkedIn Job Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green)](https://flask.palletsprojects.com/)
[![Render](https://img.shields.io/badge/Deployed%20on-Render-46a2f1)](https://render.com)

A full-stack web application that provides data-driven insights into job market trends by analyzing LinkedIn job postings. Discover in-demand skills, geographic hotspots, and market trends to make smarter career decisions.

**🌐 Live Demo: [https://jobintellect.onrender.com](https://jobintellect.onrender.com)**

---

##  What is JobIntellect?

JobIntellect is a smart job market analytics platform that scrapes LinkedIn job postings and provides valuable insights about:
- **Skills demand** - What technologies companies are actually hiring for
- **Geographic trends** - Where jobs are concentrated geographically  
- **Market analysis** - Real-time data on job availability and competition
- **Career planning** - Data-driven guidance for skill development

###  Perfect For:
- **Job Seekers** - Understand what skills to learn for target roles
- **Students** - Plan your career path based on market demand
- **Recruiters** - Analyze market trends and skill availability
- **Career Coaches** - Provide data-backed career advice

---

## Features

### Smart Job Search
- **Advanced LinkedIn Integration** - Public API and authenticated scraping
- **Real-time Data** - Fresh job postings with detailed information
- **Flexible Filtering** - Search by keywords, location, and industry

### Analytics & Insights
- **Skills Frequency Analysis** - Identify most in-demand technologies
- **Geographic Heat Mapping** - See where jobs are concentrated
- **Market Trends** - Track job availability over time
- **Industry Breakdown** - Understand sector-specific demands

### Data Management
- **SQLite Database** - Persistent storage of search results and analytics
- **Export Capabilities** - Download data as JSON or CSV
- **Session Management** - Track multiple search sessions
- **Admin Dashboard** - Monitor database statistics and usage

### User Experience
- **Responsive Design** - Works perfectly on desktop and mobile
- **Interactive Charts** - Beautiful visualizations with Chart.js
- **Professional UI** - Clean, LinkedIn-inspired interface
- **Real-time Updates** - Live search results and analytics

---

## 🛠 Tech Stack

### **Backend**
- **Framework**: Flask (Python)
- **Database**: SQLite with SQLAlchemy-style operations
- **Web Scraping**: BeautifulSoup4, Requests
- **Authentication**: Session-based with secure cookies
- **API**: RESTful endpoints with JSON responses

### **Frontend**
- **UI Framework**: Bootstrap 5
- **Charts**: Chart.js for data visualization
- **Styling**: Custom CSS with LinkedIn-inspired design
- **JavaScript**: Vanilla JS with modern ES6+ features

### **Deployment & DevOps**
- **Platform**: Render (Cloud hosting)
- **Server**: Gunicorn WSGI server
- **Environment**: Python 3.11+
- **Dependencies**: Pip with requirements.txt

---

## Quick Start

### Prerequisites
- Python 3.11 or higher
- Git

### Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/jobintellect.git
   cd jobintellect