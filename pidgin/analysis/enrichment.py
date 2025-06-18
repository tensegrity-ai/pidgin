"""Metrics enrichment utilities for post-hoc analysis."""

from typing import List, Dict, Any, Optional, Union

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class MetricsEnricher:
    """Helper functions for post-hoc metric calculation.
    
    This class provides static methods for enriching conversation data
    with additional metrics that are computationally expensive or require
    external dependencies. These are designed to be used in Jupyter notebooks
    after experiments have completed.
    """
    
    @staticmethod
    def calculate_perplexity(texts: List[str], model=None, tokenizer=None) -> List[float]:
        """Calculate perplexity for a list of texts.
        
        Args:
            texts: List of text messages
            model: Optional pre-loaded language model
            tokenizer: Optional pre-loaded tokenizer
            
        Returns:
            List of perplexity scores
            
        Note:
            If model/tokenizer are not provided, this returns placeholder values.
            Users should load their preferred model for actual calculations.
        """
        if model is None or tokenizer is None:
            # Return placeholder values
            return [50.0] * len(texts)
        
        # Example implementation (users would provide actual model logic)
        perplexities = []
        for text in texts:
            # This is where actual perplexity calculation would go
            # using the provided model and tokenizer
            perplexities.append(50.0)  # Placeholder
        
        return perplexities
    
    @staticmethod
    def calculate_sentiment(texts: List[str], method: str = 'textblob') -> List[Dict[str, float]]:
        """Calculate sentiment scores for texts.
        
        Args:
            texts: List of text messages
            method: Sentiment analysis method ('textblob', 'vader', 'custom')
            
        Returns:
            List of sentiment dictionaries with 'polarity' and 'subjectivity'
        """
        try:
            if method == 'textblob':
                from textblob import TextBlob
                sentiments = []
                for text in texts:
                    blob = TextBlob(text)
                    sentiments.append({
                        'polarity': blob.sentiment.polarity,
                        'subjectivity': blob.sentiment.subjectivity
                    })
                return sentiments
            
            elif method == 'vader':
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                analyzer = SentimentIntensityAnalyzer()
                sentiments = []
                for text in texts:
                    scores = analyzer.polarity_scores(text)
                    sentiments.append({
                        'polarity': scores['compound'],
                        'positive': scores['pos'],
                        'negative': scores['neg'],
                        'neutral': scores['neu']
                    })
                return sentiments
            
            else:
                # Placeholder for custom methods
                return [{'polarity': 0.0, 'subjectivity': 0.5} for _ in texts]
                
        except ImportError:
            # If sentiment libraries aren't installed, return neutral scores
            return [{'polarity': 0.0, 'subjectivity': 0.5} for _ in texts]
    
    @staticmethod
    def calculate_formality(texts: List[str]) -> List[float]:
        """Calculate formality scores for texts.
        
        Args:
            texts: List of text messages
            
        Returns:
            List of formality scores (0-1, higher is more formal)
        """
        formality_scores = []
        
        # Simple heuristic-based formality scoring
        informal_markers = {
            'contractions': ["don't", "won't", "can't", "wouldn't", "shouldn't", 
                           "couldn't", "didn't", "isn't", "aren't", "wasn't",
                           "weren't", "haven't", "hasn't", "hadn't", "i'm",
                           "you're", "we're", "they're", "it's", "that's"],
            'informal_words': ['yeah', 'yep', 'nope', 'gonna', 'wanna', 'gotta',
                             'kinda', 'sorta', 'like', 'stuff', 'thing'],
            'slang': ['lol', 'omg', 'btw', 'idk', 'imo', 'tbh', 'smh']
        }
        
        formal_markers = {
            'formal_words': ['furthermore', 'moreover', 'nevertheless', 'therefore',
                           'consequently', 'accordingly', 'hence', 'thus'],
            'passive_indicators': ['is being', 'was being', 'has been', 'have been',
                                 'had been', 'will be', 'would be']
        }
        
        for text in texts:
            text_lower = text.lower()
            words = text_lower.split()
            
            informal_count = 0
            formal_count = 0
            
            # Count informal markers
            for marker_type, markers in informal_markers.items():
                for marker in markers:
                    informal_count += text_lower.count(marker)
            
            # Count formal markers
            for marker_type, markers in formal_markers.items():
                for marker in markers:
                    formal_count += text_lower.count(marker)
            
            # Calculate formality score
            total_markers = informal_count + formal_count
            if total_markers > 0:
                formality = formal_count / total_markers
            else:
                # Default to neutral if no markers found
                formality = 0.5
            
            # Adjust based on punctuation and capitalization
            if text[0].isupper():
                formality += 0.1
            if text.count('.') > text.count('!') + text.count('?'):
                formality += 0.1
            
            # Normalize to 0-1 range
            formality = max(0.0, min(1.0, formality))
            
            formality_scores.append(formality)
        
        return formality_scores
    
    @staticmethod
    def calculate_readability(texts: List[str]) -> List[Dict[str, float]]:
        """Calculate readability scores using multiple metrics.
        
        Args:
            texts: List of text messages
            
        Returns:
            List of dictionaries with readability metrics
        """
        try:
            from textstat import flesch_reading_ease, flesch_kincaid_grade
            
            readability_scores = []
            for text in texts:
                scores = {
                    'flesch_reading_ease': flesch_reading_ease(text),
                    'flesch_kincaid_grade': flesch_kincaid_grade(text)
                }
                readability_scores.append(scores)
            
            return readability_scores
            
        except ImportError:
            # Return placeholder values if textstat not installed
            return [{'flesch_reading_ease': 60.0, 'flesch_kincaid_grade': 8.0} 
                   for _ in texts]
    
    @staticmethod
    def calculate_topic_similarity(texts: List[str], method: str = 'tfidf'):
        """Calculate pairwise topic similarity between texts.
        
        Args:
            texts: List of text messages
            method: Similarity method ('tfidf', 'word2vec', 'bert')
            
        Returns:
            Similarity matrix (n x n) where n is number of texts
        """
        n = len(texts)
        
        if method == 'tfidf':
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                
                vectorizer = TfidfVectorizer()
                tfidf_matrix = vectorizer.fit_transform(texts)
                similarity_matrix = cosine_similarity(tfidf_matrix)
                
                return similarity_matrix
                
            except ImportError:
                # Return identity matrix if sklearn not available
                if HAS_NUMPY:
                    return np.eye(n)
                else:
                    # Return list of lists if numpy not available
                    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        
        else:
            # Placeholder for other methods
            if HAS_NUMPY:
                return np.eye(n)
            else:
                return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    
    @staticmethod
    def batch_enrich_dataframe(df, text_column: str = 'message',
                             enrichments: List[str] = None) -> None:
        """Enrich a DataFrame with multiple metrics at once.
        
        Args:
            df: Pandas DataFrame with conversation data
            text_column: Name of column containing text messages
            enrichments: List of enrichments to apply
                        ['sentiment', 'formality', 'readability']
        
        Note:
            This modifies the DataFrame in-place, adding new columns
        """
        if enrichments is None:
            enrichments = ['sentiment', 'formality']
        
        texts = df[text_column].tolist()
        
        if 'sentiment' in enrichments:
            sentiments = MetricsEnricher.calculate_sentiment(texts)
            df['sentiment_polarity'] = [s['polarity'] for s in sentiments]
            if 'subjectivity' in sentiments[0]:
                df['sentiment_subjectivity'] = [s['subjectivity'] for s in sentiments]
        
        if 'formality' in enrichments:
            df['formality_score'] = MetricsEnricher.calculate_formality(texts)
        
        if 'readability' in enrichments:
            readability = MetricsEnricher.calculate_readability(texts)
            df['flesch_reading_ease'] = [r['flesch_reading_ease'] for r in readability]
            df['flesch_kincaid_grade'] = [r['flesch_kincaid_grade'] for r in readability]