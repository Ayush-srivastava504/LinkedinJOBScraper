max result want 6 only
import requests
from bs4 import BeautifulSoup
import time
import random
import json
import csv
from datetime import datetime
import re
import os
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import uuid
import sqlite3
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-for-render')

# SQLite Database Configuration
DATABASE = 'job_analytics.db'

def get_db_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize SQLite database tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("Initializing database tables...")
        
        # Create search_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_sessions (
                id TEXT PRIMARY KEY,
                keywords TEXT,
                location TEXT,
                max_results INTEGER,
                use_auth BOOLEAN,
                searched_at DATETIME,
                total_jobs INTEGER
            )
        ''')
        
        # Create jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                title TEXT,
                company TEXT,
                location TEXT,
                url TEXT,
                post_date TEXT,
                scraped_at DATETIME,
                source TEXT,
                description TEXT,
                industry TEXT,
                FOREIGN KEY (session_id) REFERENCES search_sessions(id)
            )
        ''')
        
        # Create job_skills table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                skill TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON jobs(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_skill ON job_skills(skill)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_id ON job_skills(job_id)')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

class AdvancedLinkedInScraper:
    def __init__(self, session_cookie=None, user_agent=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        if session_cookie:
            self.session.cookies.set('li_at', session_cookie)
            logger.info("Session cookie set for authenticated access")
            
        self.jobs_data = []
        self.rate_limit_delay = random.uniform(2, 4)
        self.request_timeout = 20
        self.start_time = datetime.now()

    def search_jobs_public_api(self, keywords, location=None, max_results=6):  # Changed to 6
        """Search using LinkedIn's public API"""
        logger.info(f"Searching public API for: {keywords} in {location}")
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {'keywords': keywords, 'location': location, 'start': 0}
        
        jobs_collected = 0
        max_pages = min(max_results // 6, 10)  # Reduced pages for 6 results
        
        for page in range(max_pages):
            try:
                params['start'] = page * 7
                logger.info(f"Fetching page {page + 1} from public API")
                
                response = self.session.get(base_url, params=params, timeout=self.request_timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                job_cards = soup.find_all('div', class_='base-card')
                
                if not job_cards:
                    logger.info("No more job cards found")
                    break
                
                for card in job_cards:
                    if jobs_collected >= max_results:
                        break
                        
                    job_data = self._parse_job_card_public(card)
                    if job_data:
                        self.jobs_data.append(job_data)
                        jobs_collected += 1
                
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error during public API job search: {e}")
                break
        
        logger.info(f"Public API search completed. Found {len(self.jobs_data)} jobs")
        return self.jobs_data

    def search_jobs_authenticated(self, keywords, location=None, max_results=6):  # Changed to 6
        """Search using authenticated session"""
        logger.info(f"Searching with authentication for: {keywords} in {location}")
        
        base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {'keywords': keywords, 'location': location, 'start': 0}
        
        jobs_collected = 0
        max_pages = min(max_results // 6, 10)  # Reduced pages for 6 results
        
        for page in range(max_pages):
            try:
                params['start'] = page * 6
                logger.info(f"Fetching authenticated page {page + 1}")
                
                response = self.session.get(base_url, params=params, timeout=self.request_timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                job_cards = soup.find_all('div', class_='base-card')
                
                if not job_cards:
                    logger.info("No more job cards found in authenticated search")
                    break
                
                for card in job_cards:
                    if jobs_collected >= max_results:
                        break
                        
                    job_data = self._parse_job_card_authenticated(card)
                    if job_data:
                        self.jobs_data.append(job_data)
                        jobs_collected += 1
                
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error during authenticated job search: {e}")
                break
        
        logger.info(f"Authenticated search completed. Found {len(self.jobs_data)} jobs")
        return self.jobs_data

    def _parse_job_card_public(self, card):
        """Parse job card from public API"""
        try:
            title_elem = card.find('h3', class_='base-search-card__title')
            company_elem = card.find('h4', class_='base-search-card__subtitle')
            location_elem = card.find('span', class_='job-search-card__location')
            
            if not all([title_elem, company_elem, location_elem]):
                return None
                
            title = title_elem.text.strip()
            company = company_elem.text.strip()
            location = location_elem.text.strip()
            
            link_elem = card.find('a', class_='base-card__full-link')
            job_url = link_elem['href'] if link_elem else None
            
            if job_url and '?' in job_url:
                job_url = job_url.split('?')[0]
            
            time_elem = card.find('time', class_='job-search-card__listdate')
            post_date = time_elem['datetime'] if time_elem else None
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'url': job_url,
                'post_date': post_date,
                'scraped_at': datetime.now().isoformat(),
                'source': 'public_api'
            }
            
        except Exception as e:
            logger.error(f"Error parsing public job card: {e}")
            return None

    def _parse_job_card_authenticated(self, card):
        """Parse job card for authenticated users"""
        try:
            title_elem = card.find('h3', class_='base-search-card__title')
            company_elem = card.find('h4', class_='base-search-card__subtitle')
            location_elem = card.find('span', class_='job-search-card__location')
            
            if not all([title_elem, company_elem, location_elem]):
                return None
                
            title = title_elem.text.strip()
            company = company_elem.text.strip()
            location = location_elem.text.strip()
            
            link_elem = card.find('a', class_='base-card__full-link')
            job_url = link_elem['href'] if link_elem else None
            
            if job_url:
                if '?' in job_url:
                    job_url = job_url.split('?')[0]
                if job_url.startswith('/'):
                    job_url = f"https://www.linkedin.com{job_url}"
            
            time_elem = card.find('time', class_='job-search-card__listdate')
            post_date = time_elem['datetime'] if time_elem else None
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'url': job_url,
                'post_date': post_date,
                'scraped_at': datetime.now().isoformat(),
                'source': 'authenticated'
            }
            
        except Exception as e:
            logger.error(f"Error parsing authenticated job card: {e}")
            return None

    def get_job_details(self, job_url):
        """Get detailed job information with timeout handling"""
        try:
            if not job_url:
                return {}
                
            logger.info(f"Fetching job details from: {job_url[:100]}...")
            
            detail_timeout = 15
            
            response = self.session.get(job_url, timeout=detail_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            description = ""
            description_selectors = [
                'div.description__text',
                'section.description',
                'div.description',
                'div.job-details',
                'div.job-description'
            ]
            
            for selector in description_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(separator='\n').strip()
                    if description:
                        break
            
            if not description:
                main_content = soup.find('main') or soup.find('body')
                if main_content:
                    description = main_content.get_text(separator='\n').strip()[:2000]
            
            skills = self._extract_skills_from_text(description)
            industry = self._extract_industry(soup)
            
            return {
                'description': description[:5000],
                'skills': skills,
                'industry': industry
            }
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching job details from: {job_url[:100]}...")
            return {'description': 'Timeout fetching details', 'skills': [], 'industry': ''}
        except Exception as e:
            logger.warning(f"Error getting job details: {e}")
            return {'description': f'Error: {str(e)}', 'skills': [], 'industry': ''}

    def _extract_skills_from_text(self, text):
        """Extract technical skills from job description text"""
        skill_patterns = [
            r'\b(?:Python|Java|JavaScript|TypeScript|SQL|R|Scala|C\+\+|C#|Go|Ruby|PHP|Swift|Kotlin)\b',
            r'\b(?:AWS|Azure|GCP|Google Cloud Platform|Amazon Web Services|Microsoft Azure)\b',
            r'\b(?:Docker|Kubernetes|Terraform|Ansible|Jenkins|GitLab CI|GitHub Actions)\b',
            r'\b(?:Spark|Hadoop|Kafka|Airflow|Tableau|Power BI|Looker|Snowflake)\b',
            r'\b(?:TensorFlow|PyTorch|Keras|scikit-learn|MLlib|OpenCV|NLTK|spaCy)\b',
            r'\b(?:React|Angular|Vue\.js|Node\.js|Django|Flask|Spring Boot|Express\.js)\b',
            r'\b(?:MySQL|PostgreSQL|MongoDB|Redis|Cassandra|Elasticsearch|DynamoDB)\b',
            r'\b(?:Git|SVN|Mercurial|JIRA|Confluence|Slack|Trello|Asana)\b',
            r'\b(?:REST|GraphQL|SOAP|JSON|XML|Microservices|API)\b',
            r'\b(?:Agile|Scrum|Kanban|Waterfall|DevOps|CI/CD)\b'
        ]
        
        skills = set()
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            skills.update(match for match in matches)
        
        return list(skills)

    def _extract_industry(self, soup):
        """Extract industry from job details"""
        try:
            criteria_items = soup.find_all('li', class_='description__job-criteria-item')
            for item in criteria_items:
                subtitle = item.find('h3', class_='description__job-criteria-subtitle')
                text = item.find('span', class_='description__job-criteria-text')
                if subtitle and text and 'industry' in subtitle.text.lower():
                    return text.text.strip()
        except Exception as e:
            logger.debug(f"Could not extract industry: {e}")
        return "Not specified"

    def analyze_skills_frequency(self):
        """Analyze frequency of skills in job descriptions"""
        skill_counter = {}
        for job in self.jobs_data:
            if 'details' in job and 'skills' in job['details']:
                for skill in job['details']['skills']:
                    skill_counter[skill] = skill_counter.get(skill, 0) + 1
        
        return sorted(skill_counter.items(), key=lambda x: x[1], reverse=True)

    def analyze_geographic_trends(self):
        """Analyze geographic distribution of jobs"""
        location_counter = {}
        for job in self.jobs_data:
            location = job.get('location', 'Unknown')
            location_counter[location] = location_counter.get(location, 0) + 1
        
        return sorted(location_counter.items(), key=lambda x: x[1], reverse=True)

    def enrich_jobs_with_details(self, max_details=6):  # Changed to 6
        """Enrich jobs with detailed information - limited to 6"""
        jobs_to_process = min(len(self.jobs_data), max_details)
        logger.info(f"Enriching {jobs_to_process} jobs with details")
        
        successful_details = 0
        for i, job in enumerate(self.jobs_data[:jobs_to_process]):
            try:
                if job.get('url'):
                    logger.info(f"Getting details for job {i+1}/{jobs_to_process}")
                    details = self.get_job_details(job['url'])
                    if details:
                        job['details'] = details
                        if details.get('description') and details['description'] not in ['Timeout fetching details', '']:
                            successful_details += 1
                    
                    time.sleep(random.uniform(1, 2))
                    
                    time_elapsed = (datetime.now() - self.start_time).total_seconds()
                    if time_elapsed > 60:
                        logger.info("Stopping job enrichment early to avoid timeout")
                        break
                        
            except Exception as e:
                logger.error(f"Error enriching job {i+1}: {e}")
                continue
        
        logger.info(f"Successfully enriched {successful_details} jobs with details")
        return successful_details

    def save_to_database(self, session_id, keywords, location, max_results, use_auth):
        """Save jobs data to SQLite database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM search_sessions WHERE id = ?", (session_id,))
            existing_session = cursor.fetchone()
            
            if existing_session:
                logger.info(f"Session {session_id} already exists, skipping duplicate")
                conn.close()
                return True
            
            cursor.execute('''
                INSERT INTO search_sessions (id, keywords, location, max_results, use_auth, searched_at, total_jobs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, keywords, location, max_results, use_auth, datetime.now(), len(self.jobs_data)))
            logger.info(f"Saved search session: {session_id}")
            
            jobs_saved = 0
            skills_saved = 0
            
            for job_index, job in enumerate(self.jobs_data):
                try:
                    title = job.get('title', '')[:1000]
                    company = job.get('company', '')[:500]
                    job_location = job.get('location', '')[:500]
                    url = job.get('url', '')[:1000]
                    post_date = job.get('post_date', '')
                    
                    scraped_at_str = job.get('scraped_at')
                    scraped_at = datetime.now()
                    if scraped_at_str:
                        try:
                            scraped_at = datetime.fromisoformat(scraped_at_str.replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            scraped_at = datetime.now()
                    
                    source = job.get('source', 'unknown')
                    description = job.get('details', {}).get('description', '')[:65000]
                    industry = job.get('details', {}).get('industry', '')[:500]
                    
                    cursor.execute('''
                        INSERT INTO jobs (session_id, title, company, location, url, post_date, scraped_at, source, description, industry)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (session_id, title, company, job_location, url, post_date, scraped_at, source, description, industry))
                    
                    job_id = cursor.lastrowid
                    jobs_saved += 1
                    
                    if 'details' in job and 'skills' in job['details']:
                        for skill in job['details']['skills']:
                            if skill and len(skill) <= 255:
                                cursor.execute('INSERT INTO job_skills (job_id, skill) VALUES (?, ?)', (job_id, skill))
                                skills_saved += 1
                    
                    if job_index % 10 == 0:
                        logger.info(f"Progress: {job_index + 1}/{len(self.jobs_data)} jobs saved")
                        
                except Exception as job_error:
                    logger.error(f"Failed to save job {job_index}: {job_error}")
                    continue
            
            conn.commit()
            conn.close()
            logger.info(f"Database save completed: {jobs_saved} jobs, {skills_saved} skills saved")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            return False

    def save_to_json(self, filename):
        """Save jobs data to JSON file"""
        serializable_jobs = []
        for job in self.jobs_data:
            serializable_job = job.copy()
            if 'scraped_at' in serializable_job and isinstance(serializable_job['scraped_at'], datetime):
                serializable_job['scraped_at'] = serializable_job['scraped_at'].isoformat()
            serializable_jobs.append(serializable_job)
        
        data = {
            'jobs': serializable_jobs,
            'metadata': {
                'scraped_at': datetime.now().isoformat(),
                'total_jobs': len(self.jobs_data),
                'total_with_details': sum(1 for job in self.jobs_data if 'details' in job)
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved {len(self.jobs_data)} jobs to {filename}")

    def save_to_csv(self, filename):
        """Save jobs data to CSV file"""
        if not self.jobs_data:
            return
            
        fieldnames = ['title', 'company', 'location', 'url', 'post_date', 'scraped_at', 'source', 
                     'description', 'industry', 'skills']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in self.jobs_data:
                row = {
                    'title': job.get('title', ''),
                    'company': job.get('company', ''),
                    'location': job.get('location', ''),
                    'url': job.get('url', ''),
                    'post_date': job.get('post_date', ''),
                    'scraped_at': job.get('scraped_at', ''),
                    'source': job.get('source', ''),
                    'description': job.get('details', {}).get('description', '')[:1000],
                    'industry': job.get('details', {}).get('industry', ''),
                    'skills': ', '.join(job.get('details', {}).get('skills', []))
                }
                
                writer.writerow(row)
        
        logger.info(f"Saved {len(self.jobs_data)} jobs to {filename}")

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Endpoint not found'
    }), 404

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_jobs():
    try:
        keywords = request.form.get('keywords', '').strip()
        location = request.form.get('location', '').strip()
        
        try:
            max_results = int(request.form.get('max_results', 6))  # Changed default to 6
        except (ValueError, TypeError):
            max_results = 6
            
        # Force max_results to be 6 regardless of user input
        max_results = 6
        
        use_auth = request.form.get('use_auth') == 'on'
        session_cookie = request.form.get('session_cookie', '').strip()
        
        logger.info(f"Search request received - Keywords: '{keywords}', Location: '{location}'")
        
        if not keywords:
            logger.warning("Empty keywords received")
            return jsonify({
                'success': False,
                'message': "Please enter job keywords to search."
            })
        
        # Initialize scraper
        scraper = AdvancedLinkedInScraper(
            session_cookie=session_cookie if use_auth else None
        )
        
        # Perform search
        logger.info("Starting job search...")
        if use_auth and session_cookie:
            jobs = scraper.search_jobs_authenticated(keywords, location, max_results)
        else:
            jobs = scraper.search_jobs_public_api(keywords, location, max_results)
        
        if not jobs:
            logger.info("No jobs found for search")
            return jsonify({
                'success': False,
                'message': "No jobs found. Try different keywords or location."
            })
        
        # Enrich only 6 jobs with details
        max_details = 6
        logger.info(f"Enriching {max_details} jobs with details")
        successful_details = scraper.enrich_jobs_with_details(max_details=max_details)
        
        # Analyze data
        skills_freq = scraper.analyze_skills_frequency()
        geo_trends = scraper.analyze_geographic_trends()
        
        # Generate filenames
        session_id = str(uuid.uuid4())[:8]
        json_filename = f"linkedin_jobs_{session_id}.json"
        csv_filename = f"linkedin_jobs_{session_id}.csv"
        
        # Save to database
        db_success = scraper.save_to_database(session_id, keywords, location, max_results, use_auth)
        
        # Save to files
        try:
            scraper.save_to_json(json_filename)
            scraper.save_to_csv(csv_filename)
        except Exception as file_error:
            logger.error(f"File save error: {file_error}")
        
        # Prepare response data
        response_data = {
            'success': True,
            'message': f"Found {len(jobs)} job listings for '{keywords}' in '{location}'",
            'jobs_count': len(jobs),
            'jobs_with_details': successful_details,
            'top_skills': skills_freq[:6],  # Show top 6 skills
            'top_locations': geo_trends[:6], # Show top 6 locations
            'json_filename': json_filename,
            'csv_filename': csv_filename,
            'db_success': db_success
        }
        
        logger.info(f"Search completed successfully. Jobs found: {len(jobs)}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in search_jobs: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f"An error occurred during search: {str(e)}"
        }), 500

@app.route('/results')
def results():
    jobs_data = session.get('jobs_data', [])
    skills_freq = session.get('skills_freq', [])
    geo_trends = session.get('geo_trends', [])
    
    return render_template('results.html', 
                         jobs=jobs_data, 
                         skills_frequency=skills_freq, 
                         geo_trends=geo_trends)

@app.route('/download/<filename>')
def download_file(filename):
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
        
    safe_filename = secure_filename(filename)
    try:
        return send_file(safe_filename, as_attachment=True)
    except FileNotFoundError:
        return "File not found", 404

@app.route('/database')
def database_admin():
    """Database administration page"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM jobs')
        total_jobs = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) as count FROM search_sessions')
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT skill) as count FROM job_skills')
        total_skills = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT id, keywords, location, searched_at, total_jobs 
            FROM search_sessions 
            ORDER BY searched_at DESC 
            LIMIT 10
        ''')
        recent_searches = cursor.fetchall()
        
        conn.close()
        
        return render_template('database.html',
                            total_jobs=total_jobs,
                            total_sessions=total_sessions,
                            total_skills=total_skills,
                            recent_searches=recent_searches)
        
    except Exception as e:
        logger.error(f"Database admin error: {e}")
        return f"Database error: {str(e)}", 500

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'SQLite'
    })

@app.route('/test')
def test_endpoint():
    """Test endpoint to verify server is working"""
    return jsonify({
        'success': True,
        'message': 'Server is running correctly',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == "__main__":
    init_database()
    port = int(os.environ.get('PORT', 5000))
    logger.info("Starting JobIntellect Analytics application on Render")
    app.run(host='0.0.0.0', port=port, debug=False)