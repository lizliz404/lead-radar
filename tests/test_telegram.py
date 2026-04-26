from lead_radar.telegram import TELEGRAM_TEXT_LIMIT, split_telegram_text


def test_short_text_is_single_telegram_chunk() -> None:
    chunks = list(split_telegram_text("hello"))

    assert chunks == ["hello"]


def test_long_text_is_split_under_telegram_limit() -> None:
    text = "\n\n".join(f"section {index} " + ("x" * 200) for index in range(60))

    chunks = list(split_telegram_text(text))

    assert len(chunks) > 1
    assert all(len(chunk) <= TELEGRAM_TEXT_LIMIT for chunk in chunks)
    assert "".join(chunks).replace("\n", "") in text.replace("\n", "")
