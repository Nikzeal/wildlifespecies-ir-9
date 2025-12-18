import nltk
import string
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Download only once
nltk.download("punkt_tab")
nltk.download("stopwords")

nltk.download("wordnet")
from nltk.stem import WordNetLemmatizer

STOPWORDS = set(stopwords.words("english"))
PUNCT = set(string.punctuation)

lemm = WordNetLemmatizer()

def clean_text(text):
    if not text:
        return []

    tokens = word_tokenize(text)

    cleaned = [
        lemm.lemmatize(t.lower())
        for t in tokens
        if t.lower() not in STOPWORDS and t not in PUNCT
    ]

    return " ".join(cleaned)