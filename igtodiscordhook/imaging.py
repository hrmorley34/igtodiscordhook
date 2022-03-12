import math
from os import fdopen
from pathlib import Path
from PIL import Image
from tempfile import mkstemp
from typing import Iterable, List


EXPORT_SUFFIX = ".png"


def load(path: Path) -> Image.Image:
    return Image.open(path)


def save(dir: Path, im: Image.Image) -> Path:
    fd, fname = mkstemp(dir=dir, suffix=EXPORT_SUFFIX)
    try:
        im.save(fname)
    finally:
        fdopen(fd).close()
    return Path(fname)


def combine_images_row(
    imgs: List[Image.Image], width: int, pad: int
) -> Iterable[Image.Image]:
    for i in range(0, math.ceil(len(imgs) / width)):
        yield combine_images(imgs[i * width : (i + 1) * width], width=width, pad=pad)


def combine_images(imgs: List[Image.Image], width: int, pad: int) -> Image.Image:
    if len(imgs) < 1:
        raise ValueError
    elif len(imgs) == 1:
        return imgs[0]

    size = imgs[0].size
    if len(imgs) < width:
        countwidth = len(imgs)
        countheight = 1
    else:
        countwidth = width
        countheight = math.ceil(len(imgs) / width)

    final_size = (
        countwidth * (size[0] + pad) - pad,
        countheight * (size[1] + pad) - pad,
    )
    final_image = Image.new("RGBA", final_size, (0, 0, 0, 0))

    for index, im in enumerate(imgs):
        xindex, yindex = index % width, index // width
        x = xindex * (size[0] + pad)
        y = yindex * (size[1] + pad)
        if im.size == size:
            resized = im
        # elif abs(im.size[1] / im.size[0] - size[1] / size[0]) < 0.001:
        #     # same ratio, so just resize
        #     resized = im.resize(size, Image.BICUBIC)
        else:
            resized = im.copy()
            resized.thumbnail(size, Image.BICUBIC)
            print(resized.size, resized.size == size)
            x += (size[0] - resized.width) // 2
            y += (size[1] - resized.height) // 2
        final_image.paste(resized, (x, y))

    return final_image
