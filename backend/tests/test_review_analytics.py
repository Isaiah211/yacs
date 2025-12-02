from services.review_analytics import analyze_comments


def test_analyze_comments_basic():
    comments = [
        "This class was fantastic. The professor explained concepts clearly.",
        "Terrible workload and unclear grading. I would not recommend.",
        "Good lectures but too much homework."
    ]

    result = analyze_comments(comments, top_n=2)

    assert 'avg_compound' in result
    assert 'sentiment_counts' in result
    assert 'top_positive' in result and isinstance(result['top_positive'], list)
    assert 'top_negative' in result and isinstance(result['top_negative'], list)
    # Ensure the summary is a string (may be empty)
    assert isinstance(result.get('summary', ''), str)
