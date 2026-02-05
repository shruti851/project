from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------- Startup → Investor Matching ----------
def match_startup_investors(startup_desc, investors):
    texts = [startup_desc] + [
        inv.get("preferences", "") for inv in investors
    ]

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(texts)

    similarities = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    results = []
    for i, score in enumerate(similarities):
        results.append({
            "investor_id": investors[i]["_id"],
            "name": investors[i]["name"],
            "score": round(score * 100, 2)
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)


# ---------- Founder → Talent Matching ----------
def match_talent(skills_required, talents):
    texts = [skills_required] + [
        talent.get("skills", "") for talent in talents
    ]

    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(texts)

    scores = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    matches = []
    for i, score in enumerate(scores):
        matches.append({
            "talent_id": talents[i]["_id"],
            "name": talents[i]["name"],
            "match_score": round(score * 100, 2)
        })

    return sorted(matches, key=lambda x: x["match_score"], reverse=True)
