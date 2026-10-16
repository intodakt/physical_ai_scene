"""Validate offline input dimensions and nominal camera frame rate."""

from .contract import finite_number


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError("input_profile must be an object")
    for key in ("camera", "view"):
        if not isinstance(profile.get(key), str) or not profile[key].strip():
            raise ValueError(f"input_profile requires {key}")
    for key in ("width", "height"):
        if type(profile.get(key)) is not int or profile[key] <= 0:
            raise ValueError(f"input_profile {key} must be a positive integer")
    if not finite_number(profile.get("fps")) or profile["fps"] <= 0:
        raise ValueError("input_profile fps must be positive")


def check_input(config, width, height, fps=None):
    profile = config.get("input_profile")
    if profile is None:
        return
    validate_profile(profile)
    if (width, height) != (profile["width"], profile["height"]):
        raise ValueError(
            f"Expected {profile['view']} {profile['width']}x{profile['height']}, "
            f"got {width}x{height}. Export the separate rectified left image; "
            "do not pass a side-by-side stereo frame. No automatic resizing is applied."
        )
    # Permit 29.97 FPS exports of nominal 30 FPS video; preserve the actual FPS.
    if fps is not None and (not finite_number(fps) or abs(fps - profile["fps"]) > 0.1):
        raise ValueError(f"Expected approximately {profile['fps']} FPS, got {fps}")
