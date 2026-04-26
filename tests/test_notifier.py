from lead_radar.notifier import resolve_notify_channels


def test_resolve_notify_channels_from_option_and_legacy_flags() -> None:
    channels = resolve_notify_channels("telegram,feishu", send_telegram=True)

    assert channels == ["telegram", "feishu"]


def test_resolve_notify_channels_supports_legacy_flags() -> None:
    channels = resolve_notify_channels(None, send_feishu=True, send_telegram=True)

    assert channels == ["feishu", "telegram"]
