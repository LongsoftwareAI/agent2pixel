"""Guard against vacuous visual PASS, including invisible-alpha pixel changes."""
import importlib.util
from pathlib import Path
from PIL import Image
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('compare_visual', Path(__file__).with_name('compare_visual.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def check_identical_and_one_pixel_failure(tmp_path):
    a, b = tmp_path / 'reference.png', tmp_path / 'app.png'
    image = Image.new('RGBA', (4, 4), (10, 20, 30, 255))
    image.save(a)
    image.save(b)
    assert module.compare(a, b, tmp_path / 'same.png')['passed']
    image.putpixel((0, 0), (11, 20, 30, 255))
    image.save(b)
    result = module.compare(a, b, tmp_path / 'changed.png')
    assert not result['passed'] and result['mismatch_pixels'] == 1


def check_size_mismatch_rejected(tmp_path):
    a, b = tmp_path / 'a.png', tmp_path / 'b.png'
    Image.new('RGB', (2, 2)).save(a)
    Image.new('RGB', (3, 2)).save(b)
    try:
        module.compare(a, b, tmp_path / 'diff.png')
    except ValueError as error:
        assert 'Viewport mismatch' in str(error)
    else:
        raise AssertionError('different viewport accepted')


class ComparatorTest(unittest.TestCase):
    def test_identical_and_one_pixel_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            check_identical_and_one_pixel_failure(Path(folder))

    def test_size_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            check_size_mismatch_rejected(Path(folder))


if __name__ == '__main__':
    unittest.main()
