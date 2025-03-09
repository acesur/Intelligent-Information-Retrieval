# Intelligent-Information-Retrieval
# CU Economics Search Engine - Web Interface

This is a web-based interface for the Coventry University Economics Publications Search Engine. It provides a user-friendly way to search for and explore publications by members of Coventry University's School of Economics, Finance and Accounting.

## Features

- **Web-based Interface**: Easy-to-use frontend built with Flask, Bootstrap, and jQuery
- **Publication Search**: Search publications by keywords, author, or year
- **Detailed Results**: View publication details, abstracts, and direct links to original sources
- **Admin Dashboard**: Control crawler and indexing processes, view system statistics

## Directory Structure

```
cu-economics-search-engine/
├── app.py                # Main Flask application
├── crawler.py            # Web crawler implementation
├── inverted_index.py     # Index construction
├── query_processor.py    # Query processing
├── static/               # Static files (CSS, JS, images)
├── templates/            # HTML templates
│   ├── base.html         # Base template with common elements
│   ├── index.html        # Home page template
│   ├── search.html       # Search page template
│   └── admin.html        # Admin dashboard template
├── crawled_data/         # Stored crawled publications
├── index_data/           # Inverted index files
└── README.md             # This file
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd cu-economics-search-engine
```

2. Install required dependencies:
```bash
pip install flask requests beautifulsoup4 nltk schedule
```

3. Download NLTK resources (first time only):
```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
```

## Usage

1. Run the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`

3. The web interface has three main pages:
   - **Home**: Overview of the search engine and quick search form
   - **Search**: Advanced search options and results display
   - **Admin**: System management and statistics

## User Guide

### Home Page
- Provides an overview of the search engine and its features
- Includes a quick search box
- Links to other sections of the application

### Search Page
- Enter keywords in the search field to find relevant publications
- Filter results by author name or publication year
- View search results sorted by relevance
- Click on a publication card to view detailed information
- Access links to original publication pages

### Admin Dashboard
- **Web Crawler**: Start the crawler to fetch new publications
- **Inverted Index**: Build or update the search index
- **Scheduled Tasks**: View next scheduled update or force an immediate update
- **System Logs**: View logs for different system components
- **System Statistics**: Monitor key metrics including publication count, author count, and index statistics

## Technical Details

### Frontend
- **Bootstrap 5**: For responsive and modern UI design
- **jQuery**: For dynamic content and AJAX requests
- **Font Awesome**: For icons

### Backend
- **Flask**: Web framework for Python
- **AJAX**: For asynchronous data loading and updates
- **Scheduler**: For automated weekly updates

### Search Features
- **Keyword Search**: Find publications matching specific terms
- **Author Search**: Find publications by a specific author
- **Year Search**: Find publications from a specific year
- **Combined Filters**: Combine multiple search criteria

## Deployment

For production deployment, consider the following steps:

1. Use a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn app:app
```

2. Configure a reverse proxy (like Nginx) to handle client requests

3. Set up proper logging and monitoring

4. Consider using environment variables for configuration

## License

This project is created for educational purposes as part of the Intelligent Information Retrieval module at Softwarica College.