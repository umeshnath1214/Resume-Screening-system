import re
import math
from collections import Counter

# ─── Common tech skills list ──────────────────────────────────────────────────
KNOWN_SKILLS = [
    'python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'swift', 'kotlin',
    'html', 'css', 'react', 'angular', 'vue', 'node', 'django', 'flask', 'fastapi',
    'mysql', 'postgresql', 'mongodb', 'sqlite', 'oracle', 'redis',
    'machine learning', 'deep learning', 'nlp', 'tensorflow', 'pytorch', 'scikit-learn',
    'pandas', 'numpy', 'matplotlib', 'opencv',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'linux', 'git', 'github',
    'rest api', 'graphql', 'microservices', 'agile', 'scrum',
    'data analysis', 'data science', 'artificial intelligence', 'computer vision',
    'sql', 'nosql', 'excel', 'power bi', 'tableau',
    'networking', 'cybersecurity', 'cloud computing',
    'bca', 'mca', 'b.tech', 'mtech', 'computer science',
]

STOP_WORDS = {
    'the','a','an','and','or','but','in','on','at','to','for','of','with','by',
    'from','is','are','was','were','be','been','being','have','has','had','do',
    'does','did','will','would','could','should','may','might','shall','can',
    'not','no','nor','so','yet','both','either','neither','whether','although',
    'because','since','while','after','before','as','if','that','this','these',
    'those','it','its','their','our','your','my','his','her','we','they','i',
    'you','he','she','me','him','us','them','what','which','who','whom','how',
    'when','where','why','all','each','every','both','few','more','most','some',
    'any','such','only','same','than','too','very','just','also','about','above',
    'into','through','during','including','until','against','between','without',
    'within','along','following','across','behind','beyond','plus','except',
}

def tokenize(text):
    """Lowercase, remove punctuation, split into words, remove stop words."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    tokens = [w for w in text.split() if w not in STOP_WORDS and len(w) > 1]
    return tokens

def compute_tfidf(tokens):
    """Simple single-document TF (term frequency)."""
    total = len(tokens) or 1
    freq = Counter(tokens)
    return {term: count / total for term, count in freq.items()}

def cosine_similarity(vec1, vec2):
    """Cosine similarity between two TF dicts."""
    common = set(vec1.keys()) & set(vec2.keys())
    if not common:
        return 0.0
    dot = sum(vec1[t] * vec2[t] for t in common)
    mag1 = math.sqrt(sum(v * v for v in vec1.values()))
    mag2 = math.sqrt(sum(v * v for v in vec2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

def compute_match_score(resume_text, job_description):
    """
    Match resume against job description using TF-IDF cosine similarity.
    Returns a score from 0 to 100.
    """
    if not resume_text or not job_description:
        return 0.0

    resume_tokens = tokenize(resume_text)
    job_tokens = tokenize(job_description)

    resume_vec = compute_tfidf(resume_tokens)
    job_vec = compute_tfidf(job_tokens)

    score = cosine_similarity(resume_vec, job_vec)

    # Boost score by keyword overlap in skills
    resume_lower = resume_text.lower()
    job_lower = job_description.lower()
    job_skills = [s for s in KNOWN_SKILLS if s in job_lower]
    if job_skills:
        matched = sum(1 for s in job_skills if s in resume_lower)
        skill_ratio = matched / len(job_skills)
        # Weighted: 60% cosine, 40% skill keyword overlap
        score = 0.6 * score + 0.4 * skill_ratio

    return round(min(score * 100, 100), 2)

def extract_skills(text):
    """Extract skills mentioned in the resume from the known skills list."""
    text_lower = text.lower()
    found = [skill.title() for skill in KNOWN_SKILLS if skill in text_lower]
    return list(dict.fromkeys(found))  # deduplicate preserving order

def extract_name(text):
    """Try to extract candidate name from top of resume text."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if lines:
        first = lines[0]
        if len(first.split()) <= 4 and first.replace(' ', '').isalpha():
            return first
    return "Unknown"
