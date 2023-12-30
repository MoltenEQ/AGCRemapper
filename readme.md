# AGCRemapper
---
A simple tool that allow you to create GoldSrc textures that can have their colors remapped, for example, multiplayer player models.
Made in Python using PySimpleGui and Pillow.

**Heavily work in progress!**
## Usage
1. Have a BMP file that you want to convert. Example:

 ![Base PNG](examples/test_base.bmp)

2. Create 1 or 2 masks that have the same size as the original image. Non black (#000000) areas will be seen as the parts you want to recolor. Examples:

 ![Base PNG](examples/test_mask1.bmp) (Mask 1)
 ![Base PNG](examples/test_mask2.bmp) (Mask 2)

3. Start AGCRemapper and open your files
4. Convert! The result file will be ```output.bmp```
5. Rename your file to ```Remap!_128_191_255``` where ```!``` should be replaced with a single number or capital letter of the English alphabet (0-9, A-Z). Make sure that your SMD and QC files uses the same texture names!
    * Preview thumbnails are not supported yet!
6. Compile the model with the tool of your choice (e.g.: Crowbar)
7. Enjoy!

 ![Base PNG](examples/result.gif)

---
Thanks to [The303](https://the303.org/) for his tutorials!