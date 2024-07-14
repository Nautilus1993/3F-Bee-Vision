from PIL import Image
import numpy as np


# 打开JPEG图像
# image_name = 'xingmin.jpg'

# 打开bmp原图
image_name = '1.bmp'

def jpg_to_bmp_2048(image_name):
    # 打开JPEG图像
    jpeg_image = Image.open(image_name)
    # 调整图像大小为2048x2048像素
    resized_image = jpeg_image.resize((2048, 2048))
    # 转换为8-bit的BMP图像
    bmp_image = resized_image.convert('L')
    # 保存为BMP图像
    bmp_image.save('xingmin.bmp')

# 输入2048的原图，以左下坐标x,y为起点，剪窗口宽度为w, 高度为h的窗口并存储为文件
def crop_image(x, y, w, h, image_name):
    # 计算右上角x, y坐标
    origin_image = Image.open(image_name)
    x_left = x
    x_right = x + w      # x_right - x_left = w - 1
    y_top = origin_image.size[1] - (y + h)      
    y_bottom = origin_image.size[1] - y     # y_bottom - y_top = h - 1 
    print(x_left, y_top, x_right, y_bottom)
    if x_right > 2048 or y_bottom > 2048 or x_left < 0 or y_top < 0:
        print("裁剪窗口超出原图尺寸大小！")
        return
    cropped_image = origin_image.crop((x_left, y_top, x_right, y_bottom))
    return cropped_image

test_cases = [
    [0, 0, 2048, 2048],
    [300, 400, 1024, 1024],
    [500, 500, 1024, 1024]
]

def image_size(image_name):
    image = Image.open(image_name)
    pixel_data = np.array(image)
    bytes_string = pixel_data.tobytes()
    # 打印数组形状
    print(pixel_data.shape)
    print(len(bytes_string))

def test():
    i = 1
    for t in test_cases:
        x, y, w, h = t
        print(f"开窗起点x = {x} y = {y} 开窗大小 w = {w} h = {h}")
        cropped_image = crop_image(x, y, w, h, image_name)
        cropped_image.save(str(i) + '.bmp') 
        i += 1

def main():
    # jpg_to_bmp_2048(image_name)
    test()

if __name__=="__main__":
    main()