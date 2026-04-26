from lead_radar.reddit import RedditClient


def test_reddit_client_uses_existing_access_token() -> None:
    client = RedditClient(access_token="token-from-env")

    assert client.get_access_token() == "token-from-env"
