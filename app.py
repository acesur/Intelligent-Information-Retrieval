from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import sys
import pickle
import logging
import threading
import schedule
import time
from datetime import datetime
import json

# Import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crawler import PurePortalCrawler
from inverted_index import InvertedIndex
from query_processor import QueryProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("web_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WebApp")

app = Flask(__name__)

# Global variables
data_dir = "crawled_data"
index_dir = "index_data"
query_processor = None
crawler_running = False
indexing_running = False
bg_thread = None
stop_bg_thread = False

# Create directories if they don't exist
os.makedirs(data_dir, exist_ok=True)
os.makedirs(index_dir, exist_ok=True)

# Initialize query processor
def init_query_processor():
    global query_processor
    query_processor = QueryProcessor(data_dir=data_dir, index_dir=index_dir)
    return query_processor.load_data()

# Initialize query processor at startup
init_successful = init_query_processor()
if not init_successful:
    logger.warning("Failed to initialize query processor. Search results may be unavailable.")

# Background scheduler thread
def run_scheduler():
    global stop_bg_thread
    
    # Schedule weekly crawl and index update
    schedule.every().monday.at("01:00").do(scheduled_task)
    
    while not stop_bg_thread:
        schedule.run_pending()
        time.sleep(60)

# Start background thread
bg_thread = threading.Thread(target=run_scheduler)
bg_thread.daemon = True
bg_thread.start()

# Scheduled task function
def scheduled_task():
    """Run scheduled tasks (crawler and indexing)"""
    logger.info("Running scheduled tasks")
    
    # Run crawler
    try:
        start_url = "https://pureportal.coventry.ac.uk/en/organisations/fbl-school-of-economics-finance-and-accounting"
        crawler = PurePortalCrawler(start_url)
        crawler.crawl(max_pages=200)
        logger.info(f"Scheduled crawler completed. Found {len(crawler.publications)} publications.")
    except Exception as e:
        logger.error(f"Error in scheduled crawler: {e}")
    
    # Run indexing
    try:
        index_builder = InvertedIndex()
        if os.path.exists(f"{index_dir}/index.pkl"):
            success = index_builder.update_index()
        else:
            success = index_builder.build_index()
        
        if success:
            stats = index_builder.get_statistics()
            logger.info(f"Scheduled indexing completed. Index contains {stats['total_documents']} documents and {stats['total_terms']} terms.")
        else:
            logger.error("Error in scheduled indexing")
    except Exception as e:
        logger.error(f"Error in scheduled indexing: {e}")
    
    # Reinitialize query processor
    init_query_processor()

@app.route('/')
def home():
    """Home page route"""
    return render_template('index.html')

@app.route('/search')
def search_page():
    """Search page route"""
    return render_template('search.html')

@app.route('/api/search')
def search_api():
    """API endpoint for search"""
    global query_processor
    
    # Get search parameters
    query = request.args.get('query', '')
    author = request.args.get('author', '')
    year = request.args.get('year', '')
    
    if not query and not author and not year:
        return jsonify({
            'success': False,
            'message': 'Please provide at least one search parameter',
            'results': []
        })
    
    # If query processor is not initialized, try to initialize it
    if query_processor is None:
        init_successful = init_query_processor()
        if not init_successful:
            return jsonify({
                'success': False,
                'message': 'Search engine not initialized. Please run crawler and indexing first.',
                'results': []
            })
    
    # Perform search
    results = []
    
    try:
        if query:
            results = query_processor.search(query)
        elif author:
            results = query_processor.search_by_author(author)
        elif year:
            results = query_processor.search_by_year(year)
        
        # Filter results if multiple criteria
        if author and (query or year):
            results = [r for r in results if any(author.lower() in a.lower() for a in r['authors'])]
        
        if year and (query or author):
            try:
                year_int = int(year)
                results = [r for r in results if r.get('year') == year_int]
            except ValueError:
                pass
        
        # Clean results for JSON serialization
        clean_results = []
        for result in results:
            # Convert non-serializable objects and clean the result
            clean_result = {
                'title': result.get('title', 'No title'),
                'authors': result.get('authors', []),
                'year': result.get('year', ''),
                'url': result.get('url', ''),
                'abstract': result.get('abstract', 'No abstract available'),
                'keywords': result.get('keywords', []),
                'score': float(result.get('score', 0))
            }
            clean_results.append(clean_result)
        
        return jsonify({
            'success': True,
            'message': f"Found {len(clean_results)} results",
            'results': clean_results
        })
    
    except Exception as e:
        logger.error(f"Error during search: {e}")
        return jsonify({
            'success': False,
            'message': f"Error performing search: {str(e)}",
            'results': []
        })

@app.route('/admin')
def admin_page():
    """Admin page route"""
    return render_template('admin.html')

@app.route('/api/status')
def get_status():
    """API endpoint for getting system status"""
    global crawler_running, indexing_running
    
    stats = {}
    
    # Get publication stats
    publications = []
    if os.path.exists(f"{data_dir}/publications.pkl"):
        try:
            with open(f"{data_dir}/publications.pkl", 'rb') as f:
                publications = pickle.load(f)
            stats['total_publications'] = len(publications)
            
            # Count by year
            years = {}
            for pub in publications:
                year = pub.get('year')
                if year:
                    years[year] = years.get(year, 0) + 1
            
            if years:
                stats['years_range'] = f"{min(years.keys())} - {max(years.keys())}"
                stats['most_publications_year'] = max(years.items(), key=lambda x: x[1])[0]
            
            # Count unique authors
            authors = set()
            for pub in publications:
                for author in pub.get('authors', []):
                    authors.add(author)
            
            stats['unique_authors'] = len(authors)
            
        except Exception as e:
            logger.error(f"Error loading publications for statistics: {e}")
    
    # Get index stats
    if os.path.exists(f"{index_dir}/metadata.pkl"):
        try:
            with open(f"{index_dir}/metadata.pkl", 'rb') as f:
                metadata = pickle.load(f)
                stats['avg_document_length'] = round(metadata.get('avg_document_length', 0), 2)
                stats['indexed_documents'] = metadata.get('total_documents', 0)
        except Exception as e:
            logger.error(f"Error loading index metadata for statistics: {e}")
    
    if os.path.exists(f"{index_dir}/index.pkl"):
        try:
            with open(f"{index_dir}/index.pkl", 'rb') as f:
                index = pickle.load(f)
                stats['vocabulary_size'] = len(index)
        except Exception as e:
            logger.error(f"Error loading index for statistics: {e}")
    
    # Get file system stats
    if os.path.exists(data_dir):
        data_size = sum(os.path.getsize(os.path.join(data_dir, f)) for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f)))
        stats['data_size'] = f"{data_size / (1024*1024):.2f} MB"
    
    if os.path.exists(index_dir):
        index_size = sum(os.path.getsize(os.path.join(index_dir, f)) for f in os.listdir(index_dir) if os.path.isfile(os.path.join(index_dir, f)))
        stats['index_size'] = f"{index_size / (1024*1024):.2f} MB"
    
    # Add system status
    stats['crawler_running'] = crawler_running
    stats['indexing_running'] = indexing_running
    stats['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify({
        'success': True,
        'stats': stats
    })

@app.route('/api/start_crawler', methods=['POST'])
def start_crawler():
    """API endpoint for starting the crawler"""
    global crawler_running
    
    if crawler_running:
        return jsonify({
            'success': False,
            'message': 'Crawler is already running'
        })
    
    # Run crawler in a separate thread
    def run_crawler():
        global crawler_running
        crawler_running = True
        
        try:
            start_url = "https://pureportal.coventry.ac.uk/en/organisations/fbl-school-of-economics-finance-and-accounting"
            crawler = PurePortalCrawler(start_url, data_dir=data_dir)
            crawler.crawl(max_pages=100)  # Limit for testing
            logger.info(f"Crawler completed. Found {len(crawler.publications)} publications.")
        except Exception as e:
            logger.error(f"Error running crawler: {e}")
        
        crawler_running = False
    
    thread = threading.Thread(target=run_crawler)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Crawler started'
    })

@app.route('/api/build_index', methods=['POST'])
def build_index():
    """API endpoint for building/updating the index"""
    global indexing_running
    
    if indexing_running:
        return jsonify({
            'success': False,
            'message': 'Indexing is already running'
        })
    
    # Run indexing in a separate thread
    def run_indexing():
        global indexing_running, query_processor
        indexing_running = True
        
        try:
            index_builder = InvertedIndex(data_dir=data_dir, index_dir=index_dir)
            
            # Check if index exists and update or build from scratch
            if os.path.exists(f"{index_dir}/index.pkl"):
                success = index_builder.update_index()
            else:
                success = index_builder.build_index()
            
            if success:
                stats = index_builder.get_statistics()
                logger.info(f"Indexing completed. Contains {stats['total_documents']} documents and {stats['total_terms']} terms.")
                
                # Reinitialize query processor
                init_query_processor()
            else:
                logger.error("Error building/updating index")
        except Exception as e:
            logger.error(f"Error building index: {e}")
        
        indexing_running = False
    
    thread = threading.Thread(target=run_indexing)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Indexing started'
    })

@app.route('/api/force_update', methods=['POST'])
def force_update():
    """API endpoint for forcing a scheduled update"""
    thread = threading.Thread(target=scheduled_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Forced update started'
    })

if __name__ == '__main__':
    # Run with debug=True for development, False for production
    app.run(debug=True, port=5000)