"""Strict image parity and reviewable contact sheet; no mask/threshold tuning.

Capture inputs separately under identical documented fixture settings. This helper
checks image equality only; source provenance and interaction remain separate gates.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw


def compare(reference, actual, output):
    reference, actual, output = map(Path, (reference, actual, output))
    a, b = Image.open(reference).convert('RGBA'), Image.open(actual).convert('RGBA')
    if a.size != b.size:
        raise ValueError(f'Viewport mismatch: {a.size} versus {b.size}')
    difference = ImageChops.difference(a, b)
    # Alpha differences must not hide differing RGB pixels.
    pixels = difference.tobytes()
    mismatch = sum(any(pixels[index:index + 4]) for index in range(0, len(pixels), 4))
    w, h = a.size
    sheet = Image.new('RGB', (w * 3, h + 32), '#202020')
    draw = ImageDraw.Draw(sheet)
    for i, (label, img) in enumerate((('Pinned upstream', a), ('AgentVerse', b), ('Absolute diff (RGB x4)', difference.convert('RGB').point(lambda n: min(255, n * 4))))):
        draw.text((i * w + 12, 10), label, fill='white')
        sheet.paste(img.convert('RGB'), (i * w, 32))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    result = dict(reference=str(reference), actual=str(actual), viewport=[w, h], mismatch_pixels=mismatch,
                  total_pixels=w * h, threshold_pixels=0, passed=mismatch == 0,
                  reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
                  actual_sha256=hashlib.sha256(actual.read_bytes()).hexdigest(), contact_sheet=str(output))
    output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference')
    parser.add_argument('actual')
    parser.add_argument('output')
    args = parser.parse_args()
    result = compare(args.reference, args.actual, args.output)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
