#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档重构脚本 - 最终版
1. 去除颜色样式
2. 修正图片引用路径
3. 保持Markdown图片格式
"""

import os
import re
import shutil
from pathlib import Path

BASE_DIR = r"C:\Users\Administrator\DocProjects\mianshi"
OUTPUT_DIR = os.path.join(BASE_DIR, "000最终版000")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")

def remove_color_styles(content):
    """去除所有颜色样式标签"""
    # 去除 <font style="color:..."> 标签
    content = re.sub(r'<font style="[^"]*">', '', content)
    content = re.sub(r'</font>', '', content)

    # 去除其他HTML标签
    content = re.sub(r'<[^>]+>', '', content)

    return content

def scan_images():
    """递归扫描项目根目录中的所有图片文件"""
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'}
    images = {}

    for root, dirs, files in os.walk(BASE_DIR):
        # 排除输出目录和隐藏目录
        if '.codeartsdoer' in root or '.idea' in root or '000最终版000' in root:
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in image_extensions:
                filepath = os.path.join(root, file)
                # 使用文件名作为key
                images[file] = filepath

    return images

def copy_images_to_unified_dir(images):
    """复制图片到统一目录"""
    os.makedirs(IMAGES_DIR, exist_ok=True)

    image_mapping = {}  # 原文件名 -> 新路径

    for filename, src_path in images.items():
        dst_path = os.path.join(IMAGES_DIR, filename)

        # 处理重名文件
        if os.path.exists(dst_path):
            # 如果文件已存在且内容相同，跳过
            if os.path.getsize(src_path) == os.path.getsize(dst_path):
                image_mapping[filename] = f"images/{filename}"
                continue
            # 否则添加后缀
            name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dst_path):
                dst_path = os.path.join(IMAGES_DIR, f"{name}_{counter}{ext}")
                counter += 1

        try:
            shutil.copy2(src_path, dst_path)
            rel_path = os.path.relpath(dst_path, OUTPUT_DIR)
            image_mapping[filename] = rel_path
        except Exception as e:
            print(f"  复制失败: {src_path} - {e}")

    return image_mapping

def find_best_image_match(old_filename, image_mapping):
    """找到最佳匹配的图片"""
    # 精确匹配
    if old_filename in image_mapping:
        return image_mapping[old_filename]

    # 去掉后缀中的数字后缀进行匹配
    name, ext = os.path.splitext(old_filename)
    name_without_num = re.sub(r'-\d+$', '', name)

    for filename, new_path in image_mapping.items():
        f_name, f_ext = os.path.splitext(filename)
        f_name_without_num = re.sub(r'-\d+$', '', f_name)

        if f_name_without_num == name_without_num and f_ext == ext:
            return new_path

    return None

def fix_image_references(content, image_mapping):
    """修正文档中的图片引用路径"""
    # 匹配图片引用：![alt](path) 或 ![alt](path "title")
    def replace_image_ref(match):
        alt = match.group(1)
        old_path = match.group(2)
        title = match.group(3) or ''

        # 从路径中提取文件名
        old_filename = os.path.basename(old_path)

        # 查找匹配的图片
        new_path = find_best_image_match(old_filename, image_mapping)

        if new_path:
            if title:
                return f"![{alt}]({new_path} {title})"
                return f"![{alt}]({new_path})"
            return f"![{alt}]({new_path})"

        # 如果没找到，保留原引用
        return match.group(0)

    # 替换图片引用
    content = re.sub(
        r'!\[(.*?)\]\(([^\s)]+)(?:\s+"([^"]*)")?\)',
        replace_image_ref,
        content
    )

    return content

def refactor_document(filepath, image_mapping):
    """重构单个文档"""
    print(f"  处理: {os.path.basename(filepath)}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 去除颜色样式
    content = remove_color_styles(content)

    # 修正图片引用
    content = fix_image_references(content, image_mapping)

    # 去除多余的空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    # 去除行尾空格
    content = re.sub(r' +\n', '\n', content)

    # 去除markdown中的HTML注释
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    # 去除空的图片引用
    content = re.sub(r'!\[\]\([^)]+\)', '', content)

    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return len(content)

def main():
    print("=" * 60)
    print("文档重构工具 - 最终版")
    print("=" * 60)

    # 1. 扫描图片
    print("\n[1] 扫描图片文件...")
    images = scan_images()
    print(f"  找到 {len(images)} 个图片文件")

    # 2. 复制图片到统一目录
    print("\n[2] 复制图片到统一目录...")
    image_mapping = copy_images_to_unified_dir(images)
    print(f"  复制完成: {len(image_mapping)} 个图片")

    # 3. 处理文档
    print("\n[3] 重构文档...")
    total_chars = 0
    file_count = 0

    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith('.md'):
            filepath = os.path.join(OUTPUT_DIR, filename)
            chars = refactor_document(filepath, image_mapping)
            total_chars += chars
            file_count += 1

    print(f"\n  处理完成: {file_count} 个文档, {total_chars} 字符")

    print("\n" + "=" * 60)
    print("重构完成!")
    print(f"  处理文档数: {file_count}")
    print(f"  图片目录: {IMAGES_DIR}")
    print(f"  图片数量: {len(image_mapping)}")
    print("=" * 60)

if __name__ == "__main__":
    main()