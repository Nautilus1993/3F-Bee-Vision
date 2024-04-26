import argparse
import cv2
import os
from tqdm import tqdm

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Segment Anything Model')
    parser.add_argument('--image_dir', type=str, default='data/bh/output', help='输入图像文件夹')
    parser.add_argument('--output_dir', type=str, default='data/bh/output_black', help='输出图像文件夹')
    args = parser.parse_args()

    for root, dirs, files in os.walk(args.image_dir):
        for filename in tqdm(files):
            # 获取文件扩展名
            ext = os.path.splitext(filename)[1].lower()
            # 如果扩展名不是.jpg或.png,则跳过该文件
            if ext not in ['.jpg', '.png']:
                continue
            print(filename)
            # 输入与输出完整路径
            image_path = os.path.join(root, filename)
            relative_path = os.path.relpath(image_path, args.image_dir)
            save_path = os.path.join(args.output_dir, relative_path)
            # 如果输出路径文件夹不存在则创建
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            # 输入图像
            image = cv2.imread(image_path)
            # 对图像处理, 使用相同路径下的yolo标注txt将主体扣出，背景置黑，待补全
            label_path = image_path[0:-4]+'.txt'
            # 加载yolo标注txt文件
            with open(label_path, 'r') as f:
                lines = f.readlines()

            # 解析标注信息
            for line in lines:
                line = line.strip().split()
                class_id = int(line[0])
                x_center = float(line[1])
                y_center = float(line[2])
                width = float(line[3])
                height = float(line[4])

                # 计算目标边界框的左上角和右下角坐标
                x_min = int((x_center - width / 2) * image.shape[1])
                y_min = int((y_center - height / 2) * image.shape[0])
                x_max = int((x_center + width / 2) * image.shape[1])
                y_max = int((y_center + height / 2) * image.shape[0])

                # 将标注框之内的保留，之外置黑或某个固定值，注意图像索引是[行，列]
                image[:y_min, :] = image[y_min, x_min]  # 上方区域置为左上角像素值
                image[:, :x_min] = image[y_min, x_min]  # 左侧区域置为左上角像素值
                image[y_max:, :] = image[y_min, x_min]  # 下方区域置为左上角像素值
                image[:, x_max:] = image[y_min, x_min]  # 右侧区域置为左上角像素值

            # 输出图像
            cv2.imwrite(save_path, image)
