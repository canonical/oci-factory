from src.image.pro import get_track_from_tag, has_public_tracks, is_pro_track


def test_get_track_from_tag_without_naming_assumptions():
    assert get_track_from_tag("stable") == "latest"
    assert get_track_from_tag("1.0-24.04_stable") == "1.0-24.04"
    assert get_track_from_tag("1.0-24.04") == "1.0-24.04"


def test_has_public_tracks():
    pro_config = {
        "services": ["esm-apps"],
        "config": {
            "token": "secrets.UBUNTU_PRO_TOKEN",
            "artifact-passphrase": "secrets.PRO_ARTIFACT_PASSPHRASE",
        },
    }

    assert not has_public_tracks({"release": {"1.0-24.04": {"pro": pro_config}}})
    assert not has_public_tracks(
        {"upload": [{"release": {"1.0-24.04": {"pro": pro_config}}}]}
    )
    assert has_public_tracks(
        {"release": {"1.0-24.04": {"pro": pro_config}, "latest": {}}}
    )
    assert is_pro_track({"release": {"1.0-24.04": {"pro": pro_config}}}, "1.0-24.04")
