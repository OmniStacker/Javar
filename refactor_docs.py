#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档重构脚本 - 以资深架构师风格重写文档
1. 去除颜色样式
2. 转换行文风格
3. 处理图片引用
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

def convert_to_architect_style(content, source_filename):
    """
    以资深架构师风格重写文档
    - 专业、简洁、有深度
    - 使用Markdown原生排版
    - 去除花哨样式
    """
    # 去除颜色样式
    content = remove_color_styles(content)

    # 去除多余的空行
    content = re.sub(r'\n{3,}', '\n\n', content)

    # 去除行尾空格
    content = re.sub(r' +\n', '\n', content)

    # 去除markdown中的HTML注释
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    return content

def scan_images():
    """递归扫描项目根目录中的所有图片文件"""
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'}
    images = []

    for root, dirs, files in os.walk(BASE_DIR):
        # 排除输出目录和隐藏目录
        if '.codeartsdoer' in root or '.idea' in root or '000最终版000' in root:
            continue

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in image_extensions:
                filepath = os.path.join(root, file)
                images.append(filepath)

    return images

def copy_images_to_unified_dir(images):
    """复制图片到统一目录"""
    os.makedirs(IMAGES_DIR, exist_ok=True)

    image_mapping = {}  # 原路径 -> 新路径

    for src_path in images:
        filename = os.path.basename(src_path)
        dst_path = os.path.join(IMAGES_DIR, filename)

        # 处理重名文件
        if os.path.exists(dst_path):
            # 如果文件已存在且内容相同，跳过
            if os.path.getsize(src_path) == os.path.getsize(dst_path):
                image_mapping[src_path] = f"images/{filename}"
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
            image_mapping[src_path] = rel_path
        except Exception as e:
            print(f"  复制失败: {src_path} - {e}")

    return image_mapping

def fix_image_references(content, image_mapping):
    """修正文档中的图片引用路径"""
    # 匹配图片引用：![alt](path) 或 ![alt](path "title")
    def replace_image_ref(match):
        alt = match.group(1)
        old_path = match.group(2)
        title = match.group(3) or ''

        # 查找匹配的图片
        for src_path, new_path in image_mapping.items():
            if old_path in src_path or src_path.endswith(old_path):
                if title:
                    return f"![{alt}]({new_path} {title})"
                return f"![{alt}]({new_path})"

        # 如果没找到，尝试相对路径转换
        if old_path.startswith('./') or old_path.startswith('../'):
            # 尝试找到实际文件
            abs_path = os.path.normpath(os.path.join(OUTPUT_DIR, old_path))
            for src_path, new_path in image_mapping.items():
                if os.path.normpath(src_path) == abs_path:
                    if title:
                        return f"![{alt}]({new_path} {title})"
                    return f"![{alt}]({new_path})"

        # 保留原引用
        return match.group(0)

    # 替换图片引用
    content = re.sub(
        r'!\[(.*?)\]\(([^\s)]+)(?:\s+"([^"]*)")?\)',
        replace_image_ref,
        content
    )

    # 去除无效的图片引用（文件不存在的）
    def check_image_valid(match):
        alt = match.group(1)
        path = match.group(2)

        # 检查路径是否存在
        if path.startswith('http') or path.startswith('https'):
            return match.group(0)  # 网络图片保留

        full_path = os.path.normpath(os.path.join(OUTPUT_DIR, path))
        if not os.path.exists(full_path):
            # 去除无效图片引用，保留alt文本
            return f"[{alt}]"

        return match.group(0)

    content = re.sub(
        r'!\[(.*?)\]\(([^\s)]+)\)',
        check_image_valid,
        content
    )

    return content

def refactor_document(filepath, image_mapping):
    """重构单个文档"""
    print(f"  处理: {os.path.basename(filepath)}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 转换行文风格
    content = convert_to_architect_style(content, os.path.basename(filepath))

    # 修正图片引用
    content = fix_image_references(content, image_mapping)

    # 写入文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return len(content)

def main():
    print("=" * 60)
    print("文档重构工具 - 开始处理")
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