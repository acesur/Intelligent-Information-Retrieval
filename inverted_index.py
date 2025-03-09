import pickle
import os
import re
import nltk
import logging
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from collections import defaultdict, Counter
import math

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
        logging.FileHandler("index.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("InvertedIndex")

class InvertedIndex:
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
        
        # Create index directory if it doesn't exist
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
    
    def load_publications(self):
        """Load publications data from crawler"""
        try:
            if os.path.exists(f"{self.data_dir}/publications.pkl"):
                with open(f"{self.data_dir}/publications.pkl", 'rb') as f:
                    self.publications = pickle.load(f)
                logger.info(f"Loaded {len(self.publications)} publications for indexing")
                return True
            else:
                logger.error(f"No publications data found at {self.data_dir}/publications.pkl")
                return False
        except Exception as e:
            logger.error(f"Error loading publications data: {e}")
            return False
    
    def preprocess_text(self, text):
        """Preprocess text for indexing"""
        if not text:
            return []
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and numbers
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', ' ', text)
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stop words and stem
        tokens = [self.stemmer.stem(token) for token in tokens if token not in self.stop_words and len(token) > 2]
        
        return tokens
    
    def create_document_vector(self, doc_id):
        """Create a vector representation of a document"""
        doc = self.publications[doc_id]
        
        # Combine all text fields
        text = ""
        if doc['title']:
            text += doc['title'] + " "
        
        if doc['abstract']:
            text += doc['abstract'] + " "
        
        # Add authors with higher weight (repeat to boost)
        for author in doc['authors']:
            text += author + " " + author + " "
        
        # Add keywords with higher weight
        for keyword in doc['keywords']:
            text += keyword + " " + keyword + " " + keyword + " "
        
        # Preprocess
        tokens = self.preprocess_text(text)
        
        # Count term frequencies
        term_freqs = Counter(tokens)
        
        # Store document length (number of terms)
        self.document_lengths[doc_id] = len(tokens)
        
        return term_freqs
    
    def build_index(self):
        """Build the inverted index from scratch"""
        if not self.load_publications():
            return False
        
        self.index = defaultdict(list)
        self.document_lengths = {}
        self.total_documents = len(self.publications)
        
        logger.info("Building inverted index...")
        
        # First pass: compute document vectors and update index
        for doc_id in range(self.total_documents):
            term_freqs = self.create_document_vector(doc_id)
            
            # Add entries to inverted index
            for term, freq in term_freqs.items():
                self.index[term].append((doc_id, freq))
        
        # Calculate average document length
        if self.document_lengths:
            self.avg_document_length = sum(self.document_lengths.values()) / len(self.document_lengths)
        
        # Calculate IDF for each term
        self.idf = {}
        for term, postings in self.index.items():
            self.idf[term] = math.log10(self.total_documents / len(postings))
        
        logger.info(f"Index built with {len(self.index)} terms and {self.total_documents} documents")
        
        # Save the index
        self.save_index()
        return True
    
    def update_index(self):
        """Update existing index with new documents"""
        try:
            # Load existing index
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
                
                logger.info(f"Loaded existing index with {len(self.index)} terms and {self.total_documents} documents")
            else:
                logger.info("No existing index found, building from scratch")
                return self.build_index()
            
            # Load current publications
            current_pubs = []
            if os.path.exists(f"{self.data_dir}/publications.pkl"):
                with open(f"{self.data_dir}/publications.pkl", 'rb') as f:
                    current_pubs = pickle.load(f)
            
            # Check if there are new documents
            if len(current_pubs) <= self.total_documents:
                logger.info("No new documents to index")
                return True
            
            # Update publications and index new documents
            self.publications = current_pubs
            new_docs = len(current_pubs) - self.total_documents
            logger.info(f"Updating index with {new_docs} new documents")
            
            # Index only the new documents
            for doc_id in range(self.total_documents, len(self.publications)):
                term_freqs = self.create_document_vector(doc_id)
                
                # Add entries to inverted index
                for term, freq in term_freqs.items():
                    self.index[term].append((doc_id, freq))
                    
                    # Update IDF for this term
                    self.idf[term] = math.log10(len(self.publications) / len(self.index[term]))
            
            # Update metadata
            self.total_documents = len(self.publications)
            if self.document_lengths:
                self.avg_document_length = sum(self.document_lengths.values()) / len(self.document_lengths)
            
            # Recalculate IDF for all terms
            for term in self.index:
                self.idf[term] = math.log10(self.total_documents / len(self.index[term]))
            
            logger.info(f"Index updated, now contains {len(self.index)} terms and {self.total_documents} documents")
            
            # Save the updated index
            self.save_index()
            return True
            
        except Exception as e:
            logger.error(f"Error updating index: {e}")
            return False
    
    def save_index(self):
        """Save the index to disk"""
        try:
            with open(f"{self.index_dir}/index.pkl", 'wb') as f:
                pickle.dump(self.index, f)
            
            with open(f"{self.index_dir}/document_lengths.pkl", 'wb') as f:
                pickle.dump(self.document_lengths, f)
            
            with open(f"{self.index_dir}/idf.pkl", 'wb') as f:
                pickle.dump(self.idf, f)
            
            # Save metadata
            metadata = {
                'avg_document_length': self.avg_document_length,
                'total_documents': self.total_documents,
                'last_updated': None  # Could add timestamp here
            }
            with open(f"{self.index_dir}/metadata.pkl", 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Index saved to {self.index_dir}")
            return True
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            return False
    
    def load_index(self):
        """Load the index from disk"""
        try:
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
                
                # Also load publications
                if os.path.exists(f"{self.data_dir}/publications.pkl"):
                    with open(f"{self.data_dir}/publications.pkl", 'rb') as f:
                        self.publications = pickle.load(f)
                
                return True
            else:
                logger.error(f"No index found at {self.index_dir}")
                return False
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            return False
    
    def get_statistics(self):
        """Return statistics about the index"""
        stats = {
            'total_documents': self.total_documents,
            'total_terms': len(self.index),
            'avg_document_length': self.avg_document_length,
            'vocabulary_size': len(self.index)
        }
        
        # Calculate average postings list length
        if self.index:
            postings_lengths = [len(postings) for postings in self.index.values()]
            stats['avg_postings_length'] = sum(postings_lengths) / len(postings_lengths)
            stats['max_postings_length'] = max(postings_lengths)
        
        return stats


if __name__ == "__main__":
    index_builder = InvertedIndex()
    
    # Check if index exists, update it if it does or build from scratch if not
    if os.path.exists(f"{index_builder.index_dir}/index.pkl"):
        logger.info("Updating existing index...")
        index_builder.update_index()
    else:
        logger.info("Building new index...")
        index_builder.build_index()
    
    # Print statistics
    stats = index_builder.get_statistics()
    logger.info("Index statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")