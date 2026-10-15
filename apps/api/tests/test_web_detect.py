"""Vision の掲載ページ。権利者の断定はしない。"""

from app.web_detect import pages_from_response


def test_pages_keep_https_titles_only() -> None:
    pages = pages_from_response(
        {
            "responses": [
                {
                    "webDetection": {
                        "bestGuessLabels": [{"label": "駅"}],
                        "pagesWithMatchingImages": [
                            {"url": "http://example.com/a", "pageTitle": "http は捨てる"},
                            {"url": "https://example.com/b", "pageTitle": "掲載ページ"},
                            {"url": "not-a-url", "pageTitle": "無効"},
                        ],
                    }
                }
            ]
        }
    )
    assert pages == [{"url": "https://example.com/b", "title": "掲載ページ"}]


def test_empty_response_is_empty() -> None:
    assert pages_from_response({}) == []
    assert pages_from_response({"responses": [{"webDetection": {}}]}) == []
