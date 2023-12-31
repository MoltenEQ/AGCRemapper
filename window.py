import PySimpleGUI as sg
from PIL import Image, ImageOps, ImageChops
import io
import logging
import os

file_types = [("Image Files", (".bmp", ".png", ".jpg", ".jpeg", ".gif", ".tiff", ".webp")), ("All files", ".*")]

modes = ["model","thumbnail"]
mode = "model"

file_names = {
    "model" : "RemapZ_128_191_255.bmp",
    "thumbnail" :"thumbnail.bmp"
}

thumbnail_size=(64,64)


window_layout = [
    [sg.Text("Base BMP:"), sg.Input(key="BASE_BMP_INPUT", enable_events=True), sg.FileBrowse(file_types=file_types, enable_events=True,), sg.Image(size=thumbnail_size, key="BASE_BMP_PREVIEW")],
    [sg.Text("First color mask:"), sg.Input(key="FIRST_COLOR_INPUT", enable_events=True), sg.FileBrowse(file_types=file_types, enable_events=True), sg.Image(size=thumbnail_size, key="FIRST_COLOR_PREVIEW")],
    [sg.Text("Second color mask (Optional):"), sg.Input(key="SECOND_COLOR_INPUT", enable_events=True), sg.FileBrowse(file_types=file_types, enable_events=True,), sg.Image(size=thumbnail_size, key="SECOND_COLOR_PREVIEW")],
    [sg.Text("Output folder:"), sg.Input(key="OUTPUT_FOLDER", enable_events=True), sg.FolderBrowse(),sg.Text("Mode:"),sg.Listbox(modes,key="MODE",enable_events=True,expand_y=True,default_values="model")],
    [sg.Text("Filename:"), sg.Text(file_names["model"],key="OUTPUT"), sg.Button(key="CONVERT",button_text="Convert")]
]

window = None

image_key_bases = ["BASE_BMP", "FIRST_COLOR", "SECOND_COLOR"]
image_keys = {key: {"input_key": f"{key}_INPUT", "preview_key": f"{key}_PREVIEW", "image": None} for key in image_key_bases}
image_color_formats = {
    "model" : ((0,127),(128,191),(192,255)), # 128,64,64 palette
    "thumbnail" :((0,159),(192,223),(160,191)) # special palette for thumbnails
}

def get_thumbnail_bytes(img: Image.Image, resize=None):
    """Get raw image bytes from Pillow"""
    if img is not None:
        img_copy = img.copy()
        if resize is not None:
            img_copy.thumbnail(resize)
        bytes_io = io.BytesIO()
        img_copy.save(bytes_io, format="PNG")
        return bytes_io.getvalue()
    else:
        return b''  # Return an empty bytes object when img is None



def load_images():
    global window
    for key in image_key_bases:
        file = window[key+"_INPUT"].get()
        try:
            image = Image.open(file)
            image = image.convert("RGB")
            image_keys[key]["image"] = image
            preview = get_thumbnail_bytes(image, thumbnail_size)
            window[image_keys[key]["preview_key"]].update(data=preview)
        except AttributeError:
            logging.error(f"Could not open image file: \"{file}\".")

def fill_black_color(image: Image.Image, mask: Image.Image):
    """ Fill the image with a non-black color outside the mask."""

    filled_image = Image.new("RGB", image.size)
    mask = mask.convert("1")

    for x in range(filled_image.width):
        for y in range(filled_image.height):
            mask_pixel = mask.getpixel((x, y))
            if mask_pixel == 0: # Check if the pixel is black
                filled_image.putpixel((x, y), (0,0,0))
            else:
                original_pixel = image.getpixel((x, y))
                filled_image.putpixel((x, y), original_pixel)
    return filled_image

def fill_non_black_color(image: Image.Image, mask: Image.Image):
    """ Fill the image with a non-black color outside the mask."""

    filled_image = Image.new("RGB", image.size)
    mask = mask.convert("1")

    # Get the color of the first non-black pixel inside the mask
    first_non_black_color = find_first_non_black_color(image, mask)

    if first_non_black_color is not None:
        # Fill the areas outside the mask with the color of the first non-black pixel
        for x in range(filled_image.width):
            for y in range(filled_image.height):
                mask_pixel = mask.getpixel((x, y))
                if mask_pixel == 0: # Check if the pixel is black
                    filled_image.putpixel((x, y), first_non_black_color)
                else:
                    original_pixel = image.getpixel((x, y))
                    filled_image.putpixel((x, y), original_pixel)
    else:
        # Handle the case where there is no non-black pixel inside the mask
        logging.warning("No non-black pixel found inside the mask.")

    return filled_image

def find_first_non_black_color(image: Image.Image, mask: Image.Image):
    """ Find the color of the first non-black pixel inside the mask."""
    for x in range(mask.width):
        for y in range(mask.height):
            if mask.getpixel((x, y)) != 0:  # Check if the pixel in the mask is non-black
                return image.getpixel((x, y))
    return None

def reduce_palette(image: Image.Image, palette_range):
    """Reduce the image palette to the specified range."""
    palette_size = palette_range[1] - palette_range[0] + 1  # +1 because indexing from 0
    palette_size = max(1, palette_size)  # Ensure a minimum of 1 bit
    return image.quantize(colors=palette_size, method=2)

def visualize_palette(palette):
    image = Image.new("RGB", (16, 16))
    for y in range(16):
        for x in range(16):
                index = (y * 16 + x) * 3
                color = palette[index:index + 3]
                if len(color) == 3:
                    image.putpixel((x, y), tuple(color))
                else:
                    image.putpixel((x,y),(0,0,0))

    image = image.resize((256,256),Image.NEAREST)
    return image

def convert():
    base : Image.Image = image_keys["BASE_BMP"]["image"]
    mask1 : Image.Image = image_keys["FIRST_COLOR"]["image"]
    mask2 : Image.Image = image_keys["SECOND_COLOR"]["image"]

    # Check if the images are specified and loaded

    if base is None:
        sg.popup_error("No base image specified!")
        return
    
    if mask1 is None:
        sg.popup_error("No primary mask specified!")
        return
    
    if mask2 is None:
            # Create a black image of the same size as the base if mask2 is None
            mask2 = Image.new("RGB", base.size, color=(0, 0, 0))
            logging.info("No secondary mask specified, using all blacks.")

    # Check for matching sizes
    if base.size != mask1.size or base.size != mask2.size:
        sg.popup_error("Image size mismatch! Make sure that all of your images are the same size.")
        return
    
    # Warning if thumbnail mode is selected and the image is not 200x160
    if mode == "thumbnail" and base.size != (200,160):
        result = sg.popup_ok_cancel("Images are not 200x160px. They may work not properly in the model selection screen.")
        if result =="Cancel":
            return

    # Convert masks to grayscale
    mask1_gray = ImageOps.grayscale(mask1)
    mask2_gray = ImageOps.grayscale(mask2)

    # Apply thresholding
    threshold_value = 1  # Adjust this value based on your needs
    mask1_threshold = mask1_gray.point(lambda p: p > threshold_value and 255)
    mask2_threshold = mask2_gray.point(lambda p: p > threshold_value and 255)

    mask1_threshold = mask1_threshold.convert("1")
    mask2_threshold = mask2_threshold.convert("1")

    base = base.convert("RGB")

    # Combine inverted masks using bitwise OR
    combined_mask = ImageChops.logical_or(mask1_threshold, mask2_threshold)

    combined_inverted_mask = ImageOps.invert(combined_mask)
    combined_inverted_mask = combined_inverted_mask.convert("RGB")
    mask1_threshold = mask1_threshold.convert("RGB")
    mask2_threshold = mask2_threshold.convert("RGB")

    # Create images based on masks
    base_no_color = ImageChops.multiply(base, combined_inverted_mask)

    color1 = ImageChops.multiply(base, mask1_threshold)
    color2 = ImageChops.multiply(base, mask2_threshold)

    mask1_threshold = mask1_threshold.convert("1")
    mask2_threshold = mask2_threshold.convert("1")

    mask1_inverted = ImageOps.invert(mask1_threshold)
    mask2_inverted = ImageOps.invert(mask2_threshold)

    filled_base = fill_black_color(base, combined_inverted_mask)
    filled_color1 = fill_non_black_color(color1, mask1_threshold)
    filled_color2 = fill_non_black_color(color2, mask2_threshold)

    # Switch to BMP/Palette mode and reduce the palette size to the specified ones

    base_palette_loc,c1_palette_loc,c2_palette_loc = image_color_formats[mode]

    filled_base_reduced = reduce_palette(filled_base, base_palette_loc)
    filled_color1_reduced = reduce_palette(filled_color1, c1_palette_loc)
    filled_color2_reduced = reduce_palette(filled_color2, c2_palette_loc)

    palette_filled_base = filled_base_reduced.getpalette()
    palette_filled_color1 = filled_color1_reduced.getpalette()
    palette_filled_color2 = filled_color2_reduced.getpalette()

    new_palette = [0] * (3 * 256)
    if mode == "thumbnail":
        new_palette = [0] * (3 * 14 * 16) # HACK, last two rows must not be used in thumbs

    # Assign palettes to specific positions in new_palette

    base_new_loc = (base_palette_loc[0] * 3, (len(palette_filled_base)-1) * 3)
    c1_new_loc = (c1_palette_loc[0] * 3, (len(palette_filled_color1)-1) * 3)
    c2_new_loc = (c2_palette_loc[0] * 3, (len(palette_filled_color2)-1) * 3)

    new_palette[base_new_loc[0]:base_new_loc[1]] = palette_filled_base
    new_palette[c1_new_loc[0]:c1_new_loc[1]] = palette_filled_color1
    new_palette[c2_new_loc[0]:c2_new_loc[1]] = palette_filled_color2

    # test_img = visualize_palette(new_palette)
    # test_img.show()

    filled_base_reduced.putpalette(new_palette)

    # filled_base_reduced.show()
    # filled_color1_reduced.show()
    # filled_color2_reduced.show()

    # Manually composite images
    for x in range(filled_base_reduced.width):
        for y in range(filled_base_reduced.height):
            mask2_pixel = mask2_threshold.getpixel((x, y))
            if mask2_pixel != 0:
                color2_index = filled_color2_reduced.getpixel((x, y))
                # Calculate the position of the entry in the combined palette
                color2_new_index = c2_palette_loc[0] + color2_index
                filled_base_reduced.putpixel((x, y), color2_new_index)

            mask1_pixel = mask1_threshold.getpixel((x, y))
            if mask1_pixel != 0:
                color1_index = filled_color1_reduced.getpixel((x, y))
                # Calculate the position of the entry in the combined palette
                color1_new_index = c1_palette_loc[0] + color1_index
                filled_base_reduced.putpixel((x, y), color1_new_index)

    if len(new_palette) < 3 * 256:
        new_palette.extend([0] * (3 * (256 - len(new_palette) // 3))) # HACK for the thumbnails

    # Save the image with the custom palette
    output_path = os.path.join(window["OUTPUT_FOLDER"].get(),file_names[mode])
    filled_base_reduced.save(output_path, format='BMP', mode='P', palette=new_palette)
    sg.popup_ok(f"File created as {output_path}")
    return

def main():
    # for debugging
    global window
    window = sg.Window("AGCRemapper",window_layout)

    while True: # MAIN LOOP

        event, values = window.read()

        if event == sg.WINDOW_CLOSED:
            break

        if event == "MODE":
            global mode
            mode = values["MODE"][0]
            window["OUTPUT"].update(file_names[mode])


        if event == "CONVERT":
            convert()

        for key in image_key_bases:
            if event == image_keys[key]["input_key"]:
                load_images()


    window.close()

if __name__ == "__main__":
    main()