"""
Full-Text Search System for IRODB
"""

import re
import math
from . import binary_codec as codec
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime

from .exceptions import SearchError

class FullTextSearch:
    """Full-text search engine for IRODB"""
    
    def __init__(self, db):
        self.db = db
        self.indexes = {}
        self.stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'for', 'nor', 'on', 'at', 
            'to', 'by', 'in', 'of', 'with', 'without', 'about', 'above',
            'across', 'after', 'against', 'along', 'among', 'around',
            'as', 'at', 'before', 'behind', 'below', 'beneath', 'beside',
            'between', 'beyond', 'by', 'down', 'during', 'except', 'for',
            'from', 'in', 'inside', 'into', 'like', 'near', 'of', 'off',
            'on', 'onto', 'out', 'outside', 'over', 'per', 'plus', 'since',
            'than', 'through', 'throughout', 'till', 'to', 'toward',
            'under', 'until', 'up', 'upon', 'with', 'within', 'without'
        }
        
        self.stemmer = SimpleStemmer()
    
    def create_fulltext_index(self, table_name: str, columns: List[str], 
                              index_name: str = None):
        """Create a full-text index on specified columns"""
        if table_name not in self.db.tables:
            raise SearchError(f"Table {table_name} does not exist")
        
        if index_name is None:
            index_name = f"ft_{table_name}_{'_'.join(columns)}"
        
        if index_name in self.indexes:
            raise SearchError(f"Full-text index {index_name} already exists")
        
        table_info = self.db.tables[table_name]
        table_data = codec.loads(self.db._read_page(table_info['page']))
        
        # Build inverted index
        inverted_index = defaultdict(lambda: defaultdict(float))
        document_count = len(table_data['rows'])
        
        for row in table_data['rows']:
            doc_id = row['id']
            doc_text = self._extract_text(row, columns)
            terms = self._tokenize(doc_text)
            
            # Term frequency per document
            term_counts = defaultdict(int)
            for term in terms:
                term_counts[term] += 1
            
            # Add to inverted index with TF
            for term, count in term_counts.items():
                tf = count / len(terms) if terms else 0
                inverted_index[term][doc_id] = tf
        
        # Calculate IDF for each term
        idf_cache = {}
        for term, doc_scores in inverted_index.items():
            doc_freq = len(doc_scores)
            idf = math.log((document_count + 1) / (doc_freq + 1)) + 1
            idf_cache[term] = idf
            
            # Apply IDF to scores
            for doc_id in doc_scores:
                doc_scores[doc_id] *= idf
        
        # Store index
        index_data = {
            'table': table_name,
            'columns': columns,
            'inverted_index': dict(inverted_index),
            'document_count': document_count,
            'idf_cache': idf_cache,
            'created_at': datetime.now().isoformat()
        }
        
        # Store in memory and persist
        self.indexes[index_name] = index_data
        
        # Store a codec-safe representation. Runtime postings remain dictionaries
        # for fast lookup, but binary dictionaries must have string keys. Posting
        # lists use [document_id, score] pairs so integer IDs stay typed values.
        persisted_index = dict(index_data)
        persisted_index['inverted_index'] = {
            term: [[doc_id, score] for doc_id, score in postings.items()]
            for term, postings in inverted_index.items()
        }
        index_page = self.db._get_next_page()
        self.db._write_page(index_page, codec.dumps(persisted_index))
        self.indexes[index_name]['page'] = index_page
        
        self.db._save_metadata()
        return index_name
    
    def search(self, table_name: str, query: str, 
               columns: List[str] = None,
               boost: Dict[str, float] = None,
               limit: int = 100) -> List[Dict[str, Any]]:
        """Search for documents matching the query"""
        if table_name not in self.db.tables:
            raise SearchError(f"Table {table_name} does not exist")
        
        # Find matching index
        index_name = self._find_index(table_name, columns)
        if not index_name:
            # Create temporary index
            if columns:
                index_name = self.create_fulltext_index(table_name, columns)
            else:
                raise SearchError("No full-text index found and no columns specified")
        
        index_data = self.indexes[index_name]
        inverted_index = index_data['inverted_index']
        idf_cache = index_data.get('idf_cache', {})
        
        # Parse query
        query_terms = self._tokenize(query)
        if not query_terms:
            return []
        
        # Calculate query vector
        query_tf = defaultdict(int)
        for term in query_terms:
            query_tf[term] += 1
        
        query_vector = {}
        for term, count in query_tf.items():
            idf = idf_cache.get(term, 1.0)
            tf = count / len(query_terms)
            query_vector[term] = tf * idf
        
        # Get candidate documents
        candidate_docs = set()
        for term in query_vector:
            if term in inverted_index:
                candidate_docs.update(inverted_index[term].keys())
        
        if not candidate_docs:
            return []
        
        # Calculate scores
        scores = {}
        for doc_id in candidate_docs:
            score = 0
            for term, q_weight in query_vector.items():
                if term in inverted_index and doc_id in inverted_index[term]:
                    doc_weight = inverted_index[term][doc_id]
                    score += q_weight * doc_weight
            
            # Apply field boosting
            if boost and doc_id in candidate_docs:
                # Get the actual document to check fields
                doc = self._get_document(table_name, doc_id)
                if doc:
                    field_boost_score = 0
                    for field, boost_value in boost.items():
                        if field in doc and query.lower() in str(doc[field]).lower():
                            field_boost_score += boost_value
                    score += field_boost_score
            
            scores[doc_id] = score
        
        # Sort by score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Get documents
        results = []
        for doc_id, score in sorted_docs[:limit]:
            doc = self._get_document(table_name, doc_id)
            if doc:
                doc['_score'] = score
                results.append(doc)
        
        return results
    
    def _extract_text(self, row: Dict[str, Any], columns: List[str]) -> str:
        """Extract text from specified columns"""
        texts = []
        for col in columns:
            if col in row:
                texts.append(str(row[col]))
        return ' '.join(texts)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text and apply stemming"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into words
        words = text.split()
        
        # Filter stop words and apply stemming
        tokens = []
        for word in words:
            if word not in self.stop_words and len(word) > 1:
                stemmed = self.stemmer.stem(word)
                tokens.append(stemmed)
        
        return tokens
    
    def _find_index(self, table_name: str, columns: List[str] = None) -> Optional[str]:
        """Find matching full-text index"""
        for name, index_data in self.indexes.items():
            if index_data['table'] == table_name:
                if columns is None or set(index_data['columns']) == set(columns):
                    return name
        return None
    
    def _get_document(self, table_name: str, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        table_data = codec.loads(self.db._read_page(self.db.tables[table_name]['page']))
        for row in table_data['rows']:
            if row['id'] == doc_id:
                return row.copy()
        return None
    
    def get_index_statistics(self, index_name: str) -> Dict[str, Any]:
        """Get statistics for a full-text index"""
        if index_name not in self.indexes:
            raise SearchError(f"Index {index_name} not found")
        
        index_data = self.indexes[index_name]
        inverted_index = index_data['inverted_index']
        
        term_counts = {}
        for term, docs in inverted_index.items():
            term_counts[term] = len(docs)
        
        return {
            'name': index_name,
            'table': index_data['table'],
            'columns': index_data['columns'],
            'document_count': index_data['document_count'],
            'unique_terms': len(inverted_index),
            'total_term_occurrences': sum(len(docs) for docs in inverted_index.values()),
            'top_terms': sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }


class SimpleStemmer:
    """Simple English stemmer"""
    
    def __init__(self):
        self._suffixes = {
            'ing': ['ing'],
            'ed': ['ed'],
            'es': ['es'],
            's': ['s'],
            'er': ['er'],
            'est': ['est'],
            'ly': ['ly'],
            'ful': ['ful'],
            'ness': ['ness'],
            'ment': ['ment'],
            'tion': ['tion'],
            'sion': ['sion'],
            'able': ['able'],
            'ible': ['ible'],
            'ous': ['ous']
        }
    
    def stem(self, word: str) -> str:
        """Stem a word"""
        # Handle common plural cases
        if word.endswith('ies') and len(word) > 3:
            return word[:-3] + 'y'
        if word.endswith('ves') and len(word) > 3:
            return word[:-3] + 'f'
        if word.endswith('es') and len(word) > 3:
            return word[:-2]
        if word.endswith('s') and len(word) > 2:
            if word[-2] not in 'aeiou':
                return word[:-1]
            if word.endswith('ss'):
                return word
        
        # Remove suffixes
        for suffix in ['ing', 'ed', 'ly', 'ful', 'ness', 'ment', 'tion', 'sion', 'able', 'ible', 'ous']:
            if word.endswith(suffix) and len(word) > len(suffix) + 1:
                stem = word[:-len(suffix)]
                # Handle doubling
                if len(stem) > 2 and stem[-1] == stem[-2]:
                    stem = stem[:-1]
                return stem
        
        return word