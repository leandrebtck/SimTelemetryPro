"""Generate a simple .ico file for the app using only stdlib."""
import struct
import os

def create_ico(output_path: str):
    """Create a minimal 32x32 ICO with a steering wheel icon."""
    # We'll generate a simple colored icon programmatically
    # ICO format: header + directory entry + bitmap data

    size = 32
    bpp = 32  # RGBA

    # Generate pixel data (BGRA format for .ico)
    pixels = []
    cx, cy = size / 2, size / 2
    r_outer = size / 2 - 1
    r_inner = size / 2 - 5
    r_hub   = size / 6

    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            dist = (dx*dx + dy*dy) ** 0.5

            # Outer ring
            if r_inner <= dist <= r_outer:
                # Gold ring
                pixels += [0x00, 0xB4, 0xE8, 0xFF]  # BGRA: gold #E8B400
            # Hub
            elif dist <= r_hub:
                pixels += [0x33, 0x33, 0x33, 0xFF]
            # Spokes (3 spokes)
            else:
                spoke = False
                import math
                angle = math.atan2(dy, dx)
                for spoke_a in (0, 2*math.pi/3, 4*math.pi/3):
                    diff = abs(angle - spoke_a) % math.pi
                    diff = min(diff, math.pi - diff)
                    if diff < 0.15 and r_hub < dist < r_inner:
                        spoke = True
                        break
                if spoke:
                    pixels += [0xCC, 0xCC, 0xCC, 0xFF]
                else:
                    pixels += [0x0D, 0x0D, 0x0D, 0x00]  # transparent background

    # BMP header for ICO (BITMAPINFOHEADER, 40 bytes)
    img_data = bytes(pixels)
    row_size = size * 4
    img_size = row_size * size

    # BITMAPINFOHEADER
    bmi = struct.pack(
        '<IIIHHIIIIII',
        40,           # biSize
        size,         # biWidth
        size * 2,     # biHeight (doubled for ICO, includes AND mask)
        1,            # biPlanes
        bpp,          # biBitCount
        0,            # biCompression (BI_RGB)
        img_size,     # biSizeImage
        0, 0,         # biXPelsPerMeter, biYPelsPerMeter
        0, 0,         # biClrUsed, biClrImportant
    )

    # XOR mask: pixel data (bottom-up)
    xor_data = b''
    for y in range(size - 1, -1, -1):
        xor_data += img_data[y * row_size:(y + 1) * row_size]

    # AND mask: all zeros (fully visible)
    and_row = ((size + 31) // 32) * 4  # row width in bytes, DWORD-aligned
    and_data = bytes(and_row * size)

    image_data = bmi + xor_data + and_data

    # ICO header (6 bytes)
    ico_header = struct.pack('<HHH', 0, 1, 1)  # reserved, type=1 (ICO), count=1

    # ICONDIRENTRY (16 bytes)
    data_offset = 6 + 16  # header + one entry
    ico_entry = struct.pack(
        '<BBBBHHII',
        size,           # width
        size,           # height
        0,              # color count (0 = more than 256)
        0,              # reserved
        1,              # planes
        bpp,            # bit count
        len(image_data),# size of image data
        data_offset,    # offset
    )

    with open(output_path, 'wb') as f:
        f.write(ico_header + ico_entry + image_data)

    print(f"Icon created: {output_path} ({os.path.getsize(output_path)} bytes)")


if __name__ == '__main__':
    os.makedirs('assets', exist_ok=True)
    create_ico('assets/icon.ico')
