import pickle
import os
import re
import nltk
import logging
import math
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from collections import defaultdict, Counter
import tkinter as tk
from tkinter import ttk
import webbrowser
from datetime import datetime

# Download required NLTK resources (only first time)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("search.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QueryProcessor")

class QueryProcessor:
    def __init__(self, data_dir="crawled_data", index_dir="index_data"):
        self.data_dir = data_dir
        self.index_dir = index_dir
        self.publications = []
        self.index = defaultdict(list)
        self.document_lengths = {}
        self.avg_document_length = 0
        self.total_documents = 0
        self.idf = {}
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
        
        # BM25 parameters
        self.k1 = 1.2  # Term frequency normalization
        self.b = 0.75  # Document length normalization
        
        # Load the index and publications
        self.load_data()

        # Option for partial loading
        self.use_partial_loading = True
        self.pubilcation_chunks = {}
    
    def load_data(self):
        """Load the index and publications data"""
        try:
            # Load index
            if os.path.exists(f"{self.index_dir}/index.pkl"):
                with open(f"{self.index_dir}/index.pkl", 'rb') as f:
                    self.index = pickle.load(f)
                
                with open(f"{self.index_dir}/document_lengths.pkl", 'rb') as f:
                    self.document_lengths = pickle.load(f)
                
                with open(f"{self.index_dir}/idf.pkl", 'rb') as f:
                    self.idf = pickle.load(f)
                
                with open(f"{self.index_dir}/metadata.pkl", 'rb') as f:
                    metadata = pickle.load(f)
                    self.avg_document_length = metadata.get('avg_document_length', 0)
                    self.total_documents = metadata.get('total_documents', 0)
                
                logger.info(f"Loaded index with {len(self.index)} terms and {self.total_documents} documents")
            else:
                logger.error(f"No index found at {self.index_dir}")
                return False
            pub_path = f"{self.data_dir}/publications.pkl"
            # Load publications
            if os.path.exists(pub_path):
                file_size = os.path.getsize(pub_path) / (1024 * 1024)

                if file_size > 100 and self.use_partial_loading:
                    logger.info(f"Publication file is large ({file_size:.2f} MB), using partial loading")
                    self.load_publications_metadata(pub_path)
                else:
                    with open(pub_path) as f:
                        self.publications = pickle.load(f)
                    logger.info(f"Loaded {len(self.publications)} publications")
                
            else:
                logger.error(f"No publications data found at {pub_path}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    def load_publications_metadata(self, path):
        """Load just essential metadata for efficient memory usage"""
        try:
            with open(path, 'rb') as f:
                self.publications = []
                all_pubs = pickle.load(f)

                for pub in all_pubs:
                    light_pub = {
                        'title': pub.get('Title', pub.get('title', 'Untitled')),
                        'authors': pub.get('Authors', pub.get('authors', [])),
                        'year': pub.get('Year', pub.get('year', None))
                    }
                    self.publications.append(light_pub)

                self.pubilcation_chunks = {
                    'file_path': path,
                    'count': len(all_pubs)
                }

                logger.info(f"loaded metadata for {len(self.publications)} publications")
        except Exception as e:
            logger.info(f"Error loading publication metadata: {e}")
    
    def preprocess_query(self, query_text):
        """Preprocess the query similar to document preprocessing"""
        # Convert to lowercase
        query_text = query_text.lower()
        
        # Remove punctuation and numbers
        query_text = re.sub(r'[^\w\s]', ' ', query_text)
        query_text = re.sub(r'\d+', ' ', query_text)
        
        # Tokenize
        tokens = word_tokenize(query_text)
        
        # Remove stop words and stem
        tokens = [self.stemmer.stem(token) for token in tokens if token not in self.stop_words and len(token) > 2]
        
        return tokens
    
    def search(self, query_text, max_results=10):
        """Search for publications matching the query"""
        if not self.index or not self.publications:
            logger.error("Index or publications not loaded")
            return []
        
        # Preprocess the query
        query_terms = self.preprocess_query(query_text)
        
        if not query_terms:
            logger.info("Empty query after preprocessing")
            return []
        
        logger.info(f"Searching for: {' '.join(query_terms)}")
        
        # Calculate BM25 scores for each document
        scores = defaultdict(float)
        
        for term in query_terms:
            if term in self.index:
                # Get the IDF for this term
                idf = self.idf.get(term, 0)
                
                # Iterate through each document containing this term
                for doc_id, term_freq in self.index[term]:
                    # Get document length
                    doc_length = self.document_lengths.get(doc_id, self.avg_document_length)
                    
                    # BM25 formula
                    numerator = term_freq * (self.k1 + 1)
                    denominator = term_freq + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_document_length))
                    scores[doc_id] += idf * (numerator / denominator)
        
        # Sort documents by score
        ranked_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Get the top results
        top_results = []
        for doc_id, score in ranked_docs[:max_results]:
            if doc_id < len(self.publications):
                result = self.publications[doc_id].copy()
                result['score'] = score

                #Normalize publication field names for consistent output
                if 'Title' in result and 'title' not in result:
                    result['title'] = result['Title']
                if 'Authors' in result and 'authors' not in result:
                    result['authors'] = result['Authors']
                if 'Year' in result and 'year' not in result:
                    result['year'] = result['Year']
                if 'Abstract' in result and 'abstract' not in result:
                    result['abstract'] = result['Abstract']
                if 'Publication Link' in result and 'url' not in result:
                    result['url'] = result['Publication Link']
                if 'Keywords' in result and 'keywords' not in result:
                    result['keywords'] = result['Keywords'] 
                top_results.append(result)
        
        logger.info(f"Found {len(top_results)} results")
        return top_results
    
    def search_by_author(self, author_name, max_results=10):
        """Search for publications by a specific author"""
        if not self.publications:
            logger.error("Publications not loaded")
            return []
        
        author_name = author_name.lower()
        results = []
        
        for doc_id, pub in enumerate(self.publications):
            for pub_author in pub.get('authors',[]):
                if author_name in pub_author.lower():
                    result = pub.copy()
                    result['score'] = 1.0  # Default score for author matches

                    if 'Title' in result and 'title' not in result:
                        result['title'] = result['Title']
                    if 'Authors' in result and 'authors' not in result:
                        result['authors'] = result['Authors']
                    if 'Year' in result and 'year' not in result:
                        result['year'] = result['Year']
                    if 'Abstract' in result and 'abstract' not in result:
                        result['abstract'] = result['Abstract']
                    if 'Publication Link' in result and 'url' not in result:
                        result['url'] = result['Publication Link']
                    if 'Keywords' in result and 'keywords' not in result:
                        result['keywords'] = result['Keywords'] 
                    results.append(result)
                    break
        
        # Sort by year (most recent first)
        results.sort(key=lambda x: x.get('year', 0) if 'Year' in x else x.get('year', 0), reverse=True)
        
        return results[:max_results]
    
    def search_by_year(self, year, max_results=10):
        """Search for publications from a specific year"""
        if not self.publications:
            logger.error("Publications not loaded")
            return []
        
        try:
            year = int(year)
            results = []
            
            for doc_id, pub in enumerate(self.publications):
                if pub.get('year') == year:
                    result = pub.copy()
                    result['score'] = 1.0  # Default score for year matches

                    if 'Title' in result and 'title' not in result:
                        result['title'] = result['Title']
                    if 'Authors' in result and 'authors' not in result:
                        result['authors'] = result['Authors']
                    if 'Year' in result and 'year' not in result:
                        result['year'] = result['Year']
                    if 'Abstract' in result and 'abstract' not in result:
                        result['abstract'] = result['Abstract']
                    if 'Publication Link' in result and 'url' not in result:
                        result['url'] = result['Publication Link']
                    if 'Keywords' in result and 'keywords' not in result:
                        result['keywords'] = result['Keywords'] 
                    results.append(result)
            
            return results[:max_results]
        except ValueError:
            logger.error(f"Invalid year format: {year}")
            return []


class SearchUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CU Economics Publications Search")
        self.root.geometry("1000x600")
        
        self.query_processor = QueryProcessor()
        
        # Create UI elements
        self.create_ui()
    
    def create_ui(self):
        """Create the UI elements"""
        # Frame for the search bar and buttons
        search_frame = ttk.Frame(self.root, padding="10")
        search_frame.pack(fill=tk.X)
        
        # Search bar
        ttk.Label(search_frame, text="Search:").grid(column=0, row=0, sticky=tk.W, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=50)
        self.search_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5)
        self.search_entry.bind("<Return>", self.on_search)
        
        # Search button
        search_button = ttk.Button(search_frame, text="Search", command=self.on_search)
        search_button.grid(column=2, row=0, padx=5)
        
        # Advanced search options
        ttk.Label(search_frame, text="Filter:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        
        # Author filter
        ttk.Label(search_frame, text="Author:").grid(column=1, row=1, sticky=tk.W, padx=5, pady=5)
        self.author_entry = ttk.Entry(search_frame, width=20)
        self.author_entry.grid(column=1, row=1, sticky=(tk.W, tk.E), padx=(50, 5), pady=5)
        
        # Year filter
        ttk.Label(search_frame, text="Year:").grid(column=2, row=1, sticky=tk.W, padx=5, pady=5)
        self.year_entry = ttk.Entry(search_frame, width=10)
        self.year_entry.grid(column=2, row=1, sticky=(tk.W, tk.E), padx=(40, 5), pady=5)
        
        # Results frame
        results_frame = ttk.Frame(self.root, padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Results count
        self.results_count = ttk.Label(results_frame, text="Enter a search query to begin")
        self.results_count.pack(anchor=tk.W, pady=(0, 10))
        
        # Results list with scrollbar
        self.results_tree = ttk.Treeview(results_frame, columns=("title", "authors", "year"), show="headings")
        self.results_tree.heading("title", text="Title")
        self.results_tree.heading("authors", text="Authors")
        self.results_tree.heading("year", text="Year")
        
        self.results_tree.column("title", width=400, anchor=tk.W)
        self.results_tree.column("authors", width=300, anchor=tk.W)
        self.results_tree.column("year", width=70, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click event to open publication
        self.results_tree.bind("<Double-1>", self.on_result_double_click)
        
        # Details frame
        self.details_frame = ttk.LabelFrame(self.root, text="Publication Details", padding="10")
        self.details_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Initially hide the details
        self.details_title = ttk.Label(self.details_frame, text="", wraplength=980)
        self.details_title.pack(anchor=tk.W, pady=2)
        
        self.details_authors = ttk.Label(self.details_frame, text="")
        self.details_authors.pack(anchor=tk.W, pady=2)
        
        self.details_year = ttk.Label(self.details_frame, text="")
        self.details_year.pack(anchor=tk.W, pady=2)
        
        self.details_abstract = ttk.Label(self.details_frame, text="", wraplength=980)
        self.details_abstract.pack(anchor=tk.W, pady=2)
        
        # Link buttons frame
        self.links_frame = ttk.Frame(self.details_frame)
        self.links_frame.pack(anchor=tk.W, pady=5)
        
        self.pub_link_button = ttk.Button(self.links_frame, text="Open Publication Page", state=tk.DISABLED)
        self.pub_link_button.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text=f"Ready | Index contains {self.query_processor.total_documents} publications", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def on_search(self, event=None):
        """Handle search button click or Enter key"""
        query = self.search_entry.get().strip()
        author = self.author_entry.get().strip()
        year = self.year_entry.get().strip()
        
        # Clear existing results
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)
        
        # Clear details
        self.clear_details()
        
        if not query and not author and not year:
            self.results_count.config(text="Please enter a search query, author name, or year")
            return
        
        # Perform the search
        results = []
        
        if query:
            results = self.query_processor.search(query)
        elif author:
            results = self.query_processor.search_by_author(author)
        elif year:
            results = self.query_processor.search_by_year(year)
        
        # Filter results if multiple criteria
        if author and (query or year):
            results = [r for r in results if any(author.lower() in a.lower() for a in r['authors'])]
        
        if year and (query or author):
            try:
                year_int = int(year)
                results = [r for r in results if r.get('year') == year_int]
            except ValueError:
                pass
        
        # Update results count
        self.results_count.config(text=f"Found {len(results)} publications")
        
        # Populate the results tree
        self.search_results = results  # Store for later use
        
        for i, result in enumerate(results):
            title = result.get('title', 'No title')
            authors = ', '.join(result.get('authors', ['Unknown']))
            year = result.get('year', '')
            
            self.results_tree.insert('', tk.END, iid=str(i), values=(title, authors, year))
        
        # Update status
        self.status_bar.config(text=f"Search completed | {len(results)} results found")
    
    def on_result_double_click(self, event):
        """Handle double-click on a result"""
        selected_item = self.results_tree.selection()
        if not selected_item:
            return
        
        # Get the selected result
        result_index = int(selected_item[0])
        if result_index < len(self.search_results):
            result = self.search_results[result_index]
            self.display_details(result)
    
    def display_details(self, publication):
        """Display publication details"""
        # Update labels
        self.details_title.config(text=f"Title: {publication.get('title', 'No title')}")
        self.details_authors.config(text=f"Authors: {', '.join(publication.get('authors', ['Unknown']))}")
        self.details_year.config(text=f"Year: {publication.get('year', 'Unknown')}")
        
        abstract = publication.get('abstract', 'No abstract available')
        self.details_abstract.config(text=f"Abstract: {abstract}")
        
        # Update link button
        pub_url = publication.get('url')
        if pub_url:
            self.pub_link_button.config(state=tk.NORMAL, command=lambda: webbrowser.open(pub_url))
        else:
            self.pub_link_button.config(state=tk.DISABLED)
    
    def clear_details(self):
        """Clear publication details"""
        self.details_title.config(text="")
        self.details_authors.config(text="")
        self.details_year.config(text="")
        self.details_abstract.config(text="")
        self.pub_link_button.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = SearchUI(root)
    root.mainloop()