import numpy as np
import cv2
import pyperclip


def convert_img(file_name, img_name, width, height):
    """
    Convert an image to a C-style array.

    The image is resized, converted to a 16-bit color format (5-6-5 RGB), flattened,
    and copied to the clipboard as a C array.

    :param file_name: Path to the input image.
    :param img_name: Name of the output C array.
    :param width: Target width of the image.
    :param height: Target height of the image.
    """
    img = cv2.imread(file_name).astype(np.uint16)
    img = cv2.resize(img, (width, height), interpolation=cv2.INTER_NEAREST)
    
    # Convert BGR to 5-bit Red, 6-bit Green, and 5-bit Blue
    img_r = img[:, :, 2] >> 3
    img_g = img[:, :, 1] >> 2
    img_b = img[:, :, 0] >> 3
    
    # print("First pixel values:", img_r[0, 0], img_g[0, 0], img_b[0, 0])
    
    img = (img_r << 11) + (img_g << 5) + img_b
    # print("Converted first pixel value:", img[0, 0])
    
    img = img.flatten()
    img_array = ', '.join(f"0x{x:04X}" for x in img)
    output_code = f"short unsigned int {img_name}[{width * height}] = {{{img_array}}};"
    
    # Generate and append drawing function code
    output_code += "\n\n" + generate_draw_pixel_code(img_name, width, height)
    
    # Copy to clipboard
    # pyperclip.copy(output_code)
    # print("C array copied to clipboard.")

    # Print output result (Leo Zou added this, for Codespace use)
    # do python3 convert_img.py > output.c (creates and stores in the output.c file)
    print(output_code)


def generate_draw_pixel_code(img_name, width, height):
    """
    Generate C functions to plot and erase an image using plot_pixel().

    :param img_name: Name of the image array.
    :param width: Image width.
    :param height: Image height.
    :return: C function code as a string.
    """
    return f"""
void plot_image_{img_name}(int x, int y) {{
    for (int i = 0; i < {height}; i++) {{
        for (int j = 0; j < {width}; j++) {{
            plot_pixel(x + j, y + i, {img_name}[i * {width} + j]);
        }}
    }}
}}

void erase_image_{img_name}(int x, int y) {{
    for (int i = 0; i < {height}; i++) {{
        for (int j = 0; j < {width}; j++) {{
            plot_pixel(x + j, y + i, 0);
        }}
    }}
}}
"""

if __name__ == '__main__':
    convert_img(
        file_name=r'help_screen.png',
        img_name='help_screen_c',
        width=320,
        height=240
    )