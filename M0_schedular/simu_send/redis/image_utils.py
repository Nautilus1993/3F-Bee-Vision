from PIL import Image, ImageEnhance
import os
import time

# 打开输入图像
file_path = "/home/ywang/Documents/3F-Bee-Vision/M0_schedular/simu_send/redis/camera_image/"
input_image = Image.open(file_path)

# 定义亮度增强因子（0.0为完全黑暗，1.0为原始亮度，大于1.0为增加亮度）
brightness_factors = [0.3, 0.5, 0.7, 0.9]

# 输入一张图片的文件路径，输出生成四种亮度的图片
def generate_images(input_image, result_folder, output_image):
    for factor in brightness_factors:
        # 创建亮度增强对象
        enhancer = ImageEnhance.Brightness(input_image)      
        # 增强亮度
        output_image = enhancer.enhance(factor)
        # 保存输出图片
        output_image.save(f"{result_folder}/{output_image}_{factor * 100}.bmp")
    
# 输入为包含若干张.bmp图像的路径和星上时，输出为针对每张图，生成对应格式的一组滚动曝光图片文件
def process_images(img_dir, time_s, time_ms):
    # 创建处理结果存储路径
    if not os.path.exists(file_path):
        print("文件路径不存在！")
        return
    # 获取待处理文件列表
    img_list = sorted(os.listdir(img_dir))
    format_time = time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime(time.time()))
    result_folder = file_path + f"image_{format_time}/"
    os.makedirs(result_folder)

    # 根据星上时时间戳，生成对应的图像文件
    for img_name in img_list:
        input_image = os.path.join(img_dir, img_name)
        output_image = f"{time_s}_{time_ms}"
        generate_images(input_image, result_folder, output_image)



def main():
    time_s = 250
    time_ms = 0
    process_images(file_path)
    

if __name__=="__main__":
    main()

