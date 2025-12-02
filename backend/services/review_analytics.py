from typing import List, Dict, Any

try:
    # prefer the dedicated vader analyzer
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from nltk import sent_tokenize
except Exception:
    # lazy download of required nltk data if not present
    import nltk

    try:
        nltk.data.find('tokenizers/punkt')
    except Exception:
        nltk.download('punkt')

    try:
        nltk.data.find('sentiment/vader_lexicon')
    except Exception:
        nltk.download('vader_lexicon')

    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from nltk import sent_tokenize


def analyze_comments(comments: List[str], top_n: int = 3) -> Dict[str, Any]:
    """
    Analyze a list of review comments and return sentiment statistics

    Returns a dict with keys:
      - avg_compound: float average compound score across comments
      - sentiment_counts: dict with pos/neg/neu counts
      - top_positive: list of top positive sentences
      - top_negative: list of top negative sentences
      - summary: short summary string (extractive)
    """
    sia = SentimentIntensityAnalyzer()

    # normalize input, drop empty
    comments = [c for c in (c or "" for c in comments) if c.strip()]
    if not comments:
        return {
            'avg_compound': 0.0,
            'sentiment_counts': {'positive': 0, 'negative': 0, 'neutral': 0},
            'top_positive': [],
            'top_negative': [],
            'summary': ''
        }

    # sentence-level scoring
    sentence_scores = []  # list of (sentence, score)
    comment_compounds = []
    pos_count = neg_count = neu_count = 0

    for comment in comments:
        comp = sia.polarity_scores(comment)['compound']
        comment_compounds.append(comp)
        if comp >= 0.05:
            pos_count += 1
        elif comp <= -0.05:
            neg_count += 1
        else:
            neu_count += 1

        # split into sentences and score each
        try:
            sentences = sent_tokenize(comment)
        except Exception:
            sentences = [comment]

        for s in sentences:
            s = s.strip()
            if not s:
                continue
            score = sia.polarity_scores(s)['compound']
            sentence_scores.append((s, score))

    # compute average compound score across comments
    avg_compound = sum(comment_compounds) / len(comment_compounds)

    # pick top positive and negative sentences
    sentence_scores.sort(key=lambda t: t[1], reverse=True)
    top_positive = [s for s, _ in sentence_scores[:top_n]]

    sentence_scores.sort(key=lambda t: t[1])
    top_negative = [s for s, _ in sentence_scores[:top_n]]

    # simple extractive summary: include one positive and one negative representative
    summary_parts = []
    if top_positive:
        summary_parts.append(top_positive[0])
    if top_negative:
        # avoid duplicate
        if not top_negative[0] in summary_parts:
            summary_parts.append(top_negative[0])

    summary = " \n ".join(summary_parts)

    return {
        'avg_compound': avg_compound,
        'sentiment_counts': {'positive': pos_count, 'negative': neg_count, 'neutral': neu_count},
        'top_positive': top_positive,
        'top_negative': top_negative,
        'summary': summary
    }
