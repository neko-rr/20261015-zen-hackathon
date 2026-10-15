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


def test_images_keep_https_and_rank_full_before_similar() -> None:
    from app.web_detect import images_from_response

    images = images_from_response(
        {
            "responses": [
                {
                    "webDetection": {
                        "bestGuessLabels": [{"label": "駅"}],
                        "pagesWithMatchingImages": [
                            {
                                "url": "https://example.com/page",
                                "fullMatchingImages": [{"url": "https://example.com/full.jpg"}],
                                "partialMatchingImages": [{"url": "http://example.com/drop.jpg"}],
                            }
                        ],
                        "visuallySimilarImages": [{"url": "https://example.com/similar.jpg"}],
                    }
                }
            ]
        }
    )
    assert images[0]["match"] == "full"
    assert images[0]["page_url"] == "https://example.com/page"
    assert images[1]["match"] == "similar"
    assert all(item["url"].startswith("https://") for item in images)


def test_empty_response_is_empty() -> None:
    assert pages_from_response({}) == []
    assert pages_from_response({"responses": [{"webDetection": {}}]}) == []
