"""将8位的tiff图像转为jpg图像，可以同时处理所有子文件夹"""
import argparse
import cv2
import os
from tqdm import tqdm

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Segment Anything Model')
    parser.add_argument('--image_dir', type=str, default='data/bh/images', help='输入图像文件夹')
    parser.add_argument('--output_dir', type=str, default='data/bh/output', help='输出图像文件夹')
    args = parser.parse_args()

    for root, dirs, files in os.walk(args.image_dir):
        for filename in tqdm(files):
            # 获取文件扩展名
            ext = os.path.splitext(filename)[1].lower()
            # 如果扩展名不是.jpg或.png,则跳过该文件
            # if ext not in ['.jpg', '.png']:
            #     continue
            print(filename)
            # 输入与输出完整路径
            image_path = os.path.join(root, filename)
            relative_path = os.path.relpath(image_path, args.image_dir)
            save_path = os.path.join(args.output_dir, relative_path)
            # 如果输出路径文件夹不存在则创建
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            # 输入图像
            image = cv2.imread(image_path)
            # 对图像处理
            save_path = save_path[0:-5]+'.jpg'
            # 输出图像
            cv2.imwrite(save_path, image)

