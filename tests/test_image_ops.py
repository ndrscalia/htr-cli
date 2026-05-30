import numpy as np

from htr_cli.utils import (
    contrast_stretch,
    deslant,
    deslope,
    enhance_sauvola,
    estimate_slant,
    moment_normalize,
)


def make_diagonal_stroke(h: int = 20, w: int = 40) -> np.ndarray:
    """White background with a single diagonal black stroke."""
    img = np.full((h, w), 255, dtype=np.uint8)
    for i in range(min(h, w)):
        img[i, i] = 0
    return img


def make_blank(h: int = 20, w: int = 40, value: int = 200) -> np.ndarray:
    return np.full((h, w), value, dtype=np.uint8)


class TestContrastStretch:
    def test_shape_and_dtype_preserved(self):
        img = make_diagonal_stroke()
        out = contrast_stretch(img)
        assert out.shape == img.shape
        assert out.dtype == np.uint8

    def test_low_contrast_input_is_stretched(self):
        # input values clustered in [100, 150] should expand toward [0, 255]
        gradient = np.linspace(100, 150, 20 * 40).reshape(20, 40).astype(np.uint8)
        out = contrast_stretch(gradient)
        assert out.min() < 50
        assert out.max() > 200

    def test_uniform_input_is_returned_unchanged(self):
        # high <= low in the histogram-stretch branch → early return
        img = make_blank()
        out = contrast_stretch(img)
        assert np.array_equal(out, img)


class TestMomentNormalize:
    def test_dtype_preserved(self):
        img = make_diagonal_stroke()
        out = moment_normalize(img)
        assert out.dtype == np.uint8

    def test_width_preserved(self):
        img = make_diagonal_stroke()
        out = moment_normalize(img)
        assert out.shape[1] == img.shape[1]

    def test_uniform_input_returns_original(self):
        # no edges → Sobel moments are zero → early return
        img = make_blank()
        out = moment_normalize(img)
        assert np.array_equal(out, img)


class TestDeslope:
    def test_shape_and_dtype_preserved(self):
        img = make_diagonal_stroke()
        out = deslope(img)
        assert out.shape == img.shape
        assert out.dtype == np.uint8


class TestEstimateSlant:
    def test_returns_float(self):
        img = make_diagonal_stroke()
        angle = estimate_slant(img)
        assert isinstance(angle, float)

    def test_finite_result(self):
        img = make_diagonal_stroke()
        angle = estimate_slant(img)
        assert np.isfinite(angle)


class TestDeslant:
    def test_returns_image_and_shear(self):
        img = make_diagonal_stroke()
        result, shear = deslant(img)
        assert result.dtype == np.uint8
        assert isinstance(shear, float)

    def test_image_height_preserved(self):
        img = make_diagonal_stroke()
        result, _ = deslant(img)
        # shear transform expands width but not height
        assert result.shape[0] == img.shape[0]


class TestEnhanceSauvola:
    def test_shape_and_dtype_preserved(self):
        img = make_diagonal_stroke()
        out = enhance_sauvola(img)
        assert out.shape == img.shape
        assert out.dtype == np.uint8

    def test_uniform_input_collapses_to_white(self):
        # no local contrast anywhere → window expansion exhausts → all 255
        img = make_blank()
        out = enhance_sauvola(img)
        assert (out == 255).all()
