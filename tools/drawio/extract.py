#!/usr/bin/env python3
"""Recover the draw.io drawings that a lecture's slide PNGs were exported from.

draw.io writes the diagram's own XML into a `tEXt` chunk of every PNG it
exports, so the vectors behind these slides were never actually lost. This
pulls that chunk out, inflates it when draw.io stored it compressed, and
writes one plain `.drawio` file per PNG.

    python3 <slaidy>/tools/drawio/extract.py [sources_dir] [out_dir]   # in the lecture folder
"""
import base64
import glob
import os
import re
import struct
import sys
import urllib.parse
import zlib


def embedded_xml(png):
    """The `mxfile` XML draw.io left in this PNG, or None if there is none."""
    data = open(png, 'rb').read()
    i = 8
    while i + 12 <= len(data):
        length = struct.unpack('>I', data[i:i + 4])[0]
        kind = data[i + 4:i + 8]
        if kind == b'tEXt':
            key, _, value = data[i + 8:i + 8 + length].partition(b'\x00')
            if key == b'mxfile':
                return urllib.parse.unquote(value.decode('latin1'))
        if kind == b'IEND':
            break
        i += 12 + length
    return None


def inflate(xml):
    """Replace draw.io's compressed <diagram> payloads with plain XML."""
    def one(m):
        body = m.group(2).strip()
        if body.startswith('<'):
            return m.group(0)
        raw = zlib.decompress(base64.b64decode(body), -15).decode('utf8')
        return m.group(1) + '\n' + urllib.parse.unquote(raw) + '\n</diagram>'
    return re.sub(r'(<diagram[^>]*>)([\s\S]*?)</diagram>', one, xml)


def main(src='sources', out='drawio'):
    os.makedirs(out, exist_ok=True)
    found, plain = [], []
    for png in sorted(glob.glob(os.path.join(src, '*.png'))):
        name = os.path.basename(png)[:-4]
        xml = embedded_xml(png)
        if xml is None:
            plain.append(name)
            continue
        with open(os.path.join(out, name + '.drawio'), 'w') as f:
            f.write(inflate(xml))
        found.append(name)
    print(f'{len(found)} drawings recovered into {out}/')
    if plain:
        print(f'{len(plain)} PNGs carry no diagram (screenshots, keep as bitmap): '
              + ', '.join(plain))
    return found, plain


if __name__ == '__main__':
    main(*sys.argv[1:3])
