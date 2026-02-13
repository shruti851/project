from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# =====================================================
# STARTUP → INVESTOR MATCHING
# =====================================================
def match_startup_investors(startup_desc, investors):

    # Safety check
    if not startup_desc or not startup_desc.strip():
        return []

    if not investors:
        return []

    # Normalize text
    startup_desc = startup_desc.lower()

    texts = [startup_desc]

    for inv in investors:
        preference = inv.get("preferences", "")
        texts.append(preference.lower())

    # TF-IDF with stop words removal
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(texts)

    similarities = cosine_similarity(
        tfidf_matrix[0:1],
        tfidf_matrix[1:]
    ).flatten()

    results = []

    for i, score in enumerate(similarities):
        results.append({
            "investor_id": str(investors[i]["_id"]),
            "name": investors[i].get("name", "Unknown"),
            "score": round(float(score) * 100, 2)
        })

    # Sort highest match first
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


# =====================================================
# FOUNDER → TALENT MATCHING
# =====================================================
def match_talent(skills_required, talents):

    # Safety check
    if not skills_required or not skills_required.strip():
        return []

    if not talents:
        return []

    skills_required = skills_required.lower()

    texts = [skills_required]

    for talent in talents:
        skills = talent.get("skills", "")
        texts.append(skills.lower())

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(texts)

    scores = cosine_similarity(
        tfidf_matrix[0:1],
        tfidf_matrix[1:]
    ).flatten()

    matches = []

    for i, score in enumerate(scores):
        matches.append({
            "talent_id": str(talents[i]["_id"]),
            "name": talents[i].get("name", "Unknown"),
            "match_score": round(float(score) * 100, 2)
        })

    # Sort highest match first
    matches.sort(key=lambda x: x["match_score"], reverse=True)

    return matches
