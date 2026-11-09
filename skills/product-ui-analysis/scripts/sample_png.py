#!/usr/bin/env python3
"""Inspect/sample/crop 8-bit non-interlaced PNG without third-party packages.
Stored channels only: no ICC conversion. Reject non-opaque samples.
"""
import argparse
import collections
import hashlib
import json
import struct
import zlib
from pathlib import Path


def chunks(blob):
    if blob[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Expected PNG; convert an analysis copy with a suitable decoder.')
    pos = 8
    while pos < len(blob):
        n = struct.unpack('>I', blob[pos:pos+4])[0]
        kind, data = blob[pos+4:pos+8], blob[pos+8:pos+8+n]
        crc = struct.unpack('>I', blob[pos+8+n:pos+12+n])[0]
        if zlib.crc32(kind+data) & 0xffffffff != crc:
            raise ValueError('PNG CRC mismatch')
        yield kind, data
        pos += n+12
        if kind == b'IEND':
            return


def inspect(path):
    blob = Path(path).read_bytes()
    cs = list(chunks(blob))
    w, h, depth, color, _, _, interlace = struct.unpack('>IIBBBBB', cs[0][1])
    profile = next((d.split(b'\0')[0].decode('latin1') for k, d in cs if k == b'iCCP'), None)
    space = 'sRGB' if any(k == b'sRGB' for k, _ in cs) else 'embedded ICC: '+profile if profile else 'unspecified stored channels'
    return {'file': Path(path).name, 'width': w, 'height': h, 'bitDepth': depth,
            'colorType': color, 'interlace': interlace, 'colorSpace': space,
            'sha256': hashlib.sha256(blob).hexdigest()}


def read_png(path):
    cs = list(chunks(Path(path).read_bytes()))
    w, h, depth, color, _, _, interlace = struct.unpack('>IIBBBBB', cs[0][1])
    if depth != 8 or interlace or color not in (0, 2, 3, 4, 6):
        raise ValueError('Reader supports 8-bit non-interlaced gray/RGB/indexed/GA/RGBA PNG only.')
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    stride = w*bpp
    stream = zlib.decompress(b''.join(d for k, d in cs if k == b'IDAT'))
    if len(stream) != (stride+1)*h:
        raise ValueError('Unexpected PNG decoded length')
    palette = next((d for k, d in cs if k == b'PLTE'), b'')
    transparency = next((d for k, d in cs if k == b'tRNS'), b'')
    previous, rgba = bytearray(stride), bytearray()
    for y in range(h):
        start = y*(stride+1)
        filtering, row = stream[start], bytearray(stream[start+1:start+stride+1])
        for i in range(stride):
            a, b, c = row[i-bpp] if i >= bpp else 0, previous[i], previous[i-bpp] if i >= bpp else 0
            if filtering == 1: predictor = a
            elif filtering == 2: predictor = b
            elif filtering == 3: predictor = (a+b)//2
            elif filtering == 4:
                p = a+b-c
                distances = (abs(p-a), abs(p-b), abs(p-c))
                predictor = (a, b, c)[distances.index(min(distances))]
            elif filtering == 0: predictor = 0
            else: raise ValueError('Unknown PNG filter')
            row[i] = (row[i]+predictor) & 255
        previous = row
        for x in range(w):
            p = row[x*bpp:(x+1)*bpp]
            if color == 6: rgba.extend(p)
            elif color == 2:
                transparent = bool(transparency) and tuple(p) == struct.unpack('>HHH', transparency)
                rgba.extend(bytes(p)+bytes([0 if transparent else 255]))
            elif color == 0:
                transparent = bool(transparency) and p[0] == struct.unpack('>H', transparency)[0]
                rgba.extend(bytes([p[0], p[0], p[0], 0 if transparent else 255]))
            elif color == 4: rgba.extend(bytes([p[0], p[0], p[0], p[1]]))
            else:
                index = p[0]
                rgba.extend(palette[index*3:index*3+3]+bytes([transparency[index] if index < len(transparency) else 255]))
    return w, h, rgba


def bounds(box, w, h):
    if len(box) != 4 or not all(isinstance(v, int) for v in box):
        raise ValueError('Bounds must be four integers [x,y,width,height]')
    x, y, cw, ch = box
    if min(x, y) < 0 or min(cw, ch) <= 0 or x+cw > w or y+ch > h:
        raise ValueError('Bounds outside source image')
    return x, y, cw, ch


def crop_rgba(w, h, pixels, box):
    x, y, cw, ch = bounds(box, w, h)
    cropped = b''.join(pixels[((y+j)*w+x)*4:((y+j)*w+x+cw)*4] for j in range(ch))
    return cw, ch, cropped


def png_bytes(w, h, rgba, metadata=()):
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data) & 0xffffffff)
    raw = b''.join(b'\0'+rgba[y*w*4:(y+1)*w*4] for y in range(h))
    # Color metadata is copied, not converted; synthetic images have no implied profile.
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))+b''.join(chunk(k, d) for k, d in metadata)+chunk(b'IDAT', zlib.compress(raw))+chunk(b'IEND', b'')


def crop_png(path, box, decoded=None):
    metadata = [(k, d) for k, d in chunks(Path(path).read_bytes()) if k in (b'sRGB', b'iCCP', b'gAMA', b'cHRM')]
    return png_bytes(*crop_rgba(*(decoded or read_png(path)), box), metadata=metadata)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--box', nargs=4, type=int, metavar=('X', 'Y', 'WIDTH', 'HEIGHT'))
    parser.add_argument('--crop', help='Save crop as PNG (requires --box). Original profile is not converted.')
    parser.add_argument('--output', help='Save metadata/sample JSON')
    args = parser.parse_args()
    result = inspect(args.image)
    if args.crop and not args.box: parser.error('--crop requires --box')
    if args.box:
        w, h, rgba = crop_rgba(*read_png(args.image), args.box)
        colors = collections.Counter(bytes(rgba[i:i+4]) for i in range(0, len(rgba), 4))
        if any(p[3] != 255 for p in colors):
            raise ValueError('Sample contains transparency; record/resolve background before color measurement.')
        color, n = colors.most_common(1)[0]
        result['sample'] = {'box': args.box, 'hex': '#'+color[:3].hex().upper(),
                            'agreement': str(n)+'/'+str(w*h), 'method': 'stored-channel region mode; no ICC conversion'}
        if args.crop:
            metadata = [(k, d) for k, d in chunks(Path(args.image).read_bytes()) if k in (b'sRGB', b'iCCP', b'gAMA', b'cHRM')]
            Path(args.crop).write_bytes(png_bytes(w, h, rgba, metadata))
    value = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output: Path(args.output).write_text(value, encoding='utf-8')
    print(value)


if __name__ == '__main__':
    main()
