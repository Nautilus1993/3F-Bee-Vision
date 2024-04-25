import os
from PIL import Image

image_file = "000030.jpg"
image_bmp = "/home/ywang/Documents/3F-Bee-Vision/M0_schedular/simu_send/jpeg2raw/512.bmp"

# jpg图片转为bmp格式
# 512 * 512的图片转格式之后，加上1078Byte的文件头等，一共263222
def jpg2bmp(image_file):
    bmp_fname = os.path.splitext(image_file)[0]
    image = Image.open(image_file)
    image.save(bmp_fname + ".bmp")

def resize_bmp(image_file):
    original_image = Image.open(image_file)
    resized_image = original_image.resize((2048,2048))
    resized_image.save("2048.bmp")


resize_bmp(image_bmp)
# jpg2bmp(image_file)
