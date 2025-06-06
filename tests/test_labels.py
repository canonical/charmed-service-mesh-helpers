from contextlib import nullcontext as does_not_raise

import pytest

from charmed_service_mesh_helpers import charm_kubernetes_label


@pytest.mark.parametrize(
    "model_name, app_name, prefix, suffix, expected",
    [
        ("model", "app", "", "", "model.app"),
        ("model", "app", "prefix/", "-suffix", "prefix/model.app-suffix"),
        # Not truncated
        (
            "m" * 31,
            "a" * 31,
            "",
            "",
            f"{'m'*31}.{'a'*31}",
        ),
        # Needs truncation
        (
            "m" * 32,
            "a" * 31,
            "",
            "",
            "mmmmmmmmmmmmmmmmmmmmmmmmmmm.aaaaaaaaaaaaaaaaaaaaaaaaaaaa.c4949d",
        ),
        # Needs truncation
        (
            "m" * 33,
            "a" * 31,
            "",
            "",
            "mmmmmmmmmmmmmmmmmmmmmmmmmmmm.aaaaaaaaaaaaaaaaaaaaaaaaaaa.a4e680",
        ),
        # Needs truncation with prefix and suffix
        (
            "m" * 40,
            "a" * 40,
            "prefix/",
            "-suffix",
            "prefix/mmmmmmmmmmmmmmmmmmmm.aaaaaaaaaaaaaaaaaaaaa.499dc0-suffix",
        ),
    ],
)
def test_generate_label_cases(model_name, app_name, prefix, suffix, expected):
    label = charm_kubernetes_label(model_name, app_name, prefix, suffix)
    assert label == expected
    assert len(label) <= 63


def test_separator():
    label = charm_kubernetes_label("m"*40, "a"*40, separator="-")
    assert label == "mmmmmmmmmmmmmmmmmmmmmmmmmmm-aaaaaaaaaaaaaaaaaaaaaaaaaaaa-ba9440"
    assert len(label) <= 63


@pytest.mark.parametrize(
    "model_name, app_name, suffix, max_length, context_raised",
    [
        ("m" * 31, "a" * 31, "", 63, does_not_raise()),  # No truncation needed
        ("m" * 31, "a" * 31, "", 62, does_not_raise()),  # Truncation needed, but valid
        ("m", "a", "", 1, pytest.raises(ValueError)),  # Impossible to fit
        ("m", "a", "s" * 60, 62, pytest.raises(ValueError)),  # Suffix too long
        ("m", "a", "s" * 5, 7, pytest.raises(ValueError)),  # Suffix too long
        ("m", "a", "s" * 5, 8, does_not_raise()),  # Suffix too long
    ],
)
def test_max_length(model_name, app_name, suffix, max_length, context_raised):
    with context_raised:
        charm_kubernetes_label(model_name=model_name, app_name=app_name, suffix=suffix, max_length=max_length)


def test_truncated_labels_are_unique():
    # These would truncate to the same prefix, but should have different hashes
    label1 = charm_kubernetes_label("m" * 100, "a" * 100)
    label2 = charm_kubernetes_label("m" * 90, "a" * 90)
    assert label1 != label2
    assert len(label1) <= 63
    assert len(label2) <= 63


def test_error_on_empty_model_or_app():
    with pytest.raises(ValueError):
        charm_kubernetes_label("", "app")
    with pytest.raises(ValueError):
        charm_kubernetes_label("model", "")


@pytest.mark.parametrize(
    "model_name, app_name, prefix, suffix",
    [
        ("m", "a", "", "s" * 61),           # Suffix so long that only 1 char left for model/app
        ("m" * 60, "a", "", "s" * 54),      # Suffix + hash so long that only 1 char left for model/app
        ("m" * 60, "a", "p"*20, "s" * 34),  # Suffix + prefix + hash so long that only 1 char left for model/app
    ],
)
def test_error_on_fixed_length_too_long_cases(model_name, app_name, prefix, suffix):
    with pytest.raises(ValueError):
        charm_kubernetes_label(model_name, app_name, prefix, suffix)
