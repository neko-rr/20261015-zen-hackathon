"""見た目の呼び方は著作権検索に使わない。"""

from app.rights_query import rights_query


def test_visual_words_are_not_a_query() -> None:
    assert rights_query("女性", "駅", "") == ""
    assert rights_query("", "", "人") == ""


def test_user_title_wins_over_a_generic_name() -> None:
    assert rights_query("女性", "東京駅", "冨嶽三十六景") == "冨嶽三十六景"


def test_public_name_is_used_when_the_user_left_it_blank() -> None:
    assert rights_query("葛飾北斎", "女性", "") == "葛飾北斎"
