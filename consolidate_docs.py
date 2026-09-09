#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档整合脚本 - 将各文件夹中的文档整合为单个完整文档
"""

import os
import re
from pathlib import Path
from collections import defaultdict

BASE_DIR = r"C:\Users\Administrator\DocProjects\mianshi"
OUTPUT_DIR = os.path.join(BASE_DIR, "000最终版000")
EXCLUDE_FOLDERS = {"系列篇", "综合篇", "面试必看", "高频面试问题", "000最终版000", ".codeartsdoer", ".idea"}

def get_all_folders():
    """获取所有需要处理的文件夹"""
    folders = []
    for item in os.listdir(BASE_DIR):
        item_path = os.path.join(BASE_DIR, item)
        if os.path.isdir(item_path) and item not in EXCLUDE_FOLDERS:
            folders.append(item)
    return folders

def read_markdown_file(filepath):
    """读取markdown文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"  读取失败: {filepath} - {e}")
        return ""

def extract_sections(content):
    """提取文档中的章节标题"""
    sections = []
    lines = content.split('\n')
    for line in lines:
        # 匹配 # 开头的标题
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            sections.append((level, title, line))
    return sections

def is_duplicate_section(section_title, existing_sections):
    """检查章节是否重复"""
    # 标准化标题进行比较
    normalized = section_title.lower().strip()
    for existing in existing_sections:
        if existing.lower().strip() == normalized:
            return True
    return False

def merge_documents(folder_name, files):
    """合并文件夹中的所有文档"""
    print(f"\n处理文件夹: {folder_name}")
    print(f"  找到 {len(files)} 个文件")

    # 按文件大小排序，较大的文件优先（通常内容更完整）
    files_sorted = sorted(files, key=lambda x: x[1], reverse=True)

    merged_content = []
    existing_sections = set()
    total_chars = 0
    file_count = 0

    # 添加文档头部
    merged_content.append(f"# {folder_name}知识汇总\n")
    merged_content.append("> 本文档由多个来源整合而成，保留原始内容的完整性。\n")
    merged_content.append("---\n")

    for filepath, filesize in files_sorted:
        filename = os.path.basename(filepath)
        print(f"  读取: {filename} ({filesize} bytes)")

        content = read_markdown_file(filepath)
        if not content:
            continue

        file_count += 1
        total_chars += len(content)

        # 提取章节信息
        sections = extract_sections(content)

        # 添加来源标注
        merged_content.append(f"\n## 来源: {filename}\n")
        merged_content.append("---\n")

        # 添加内容
        merged_content.append(content)
        merged_content.append("\n")

    print(f"  整合完成: {file_count} 个文件, {total_chars} 字符")
    return ''.join(merged_content), total_chars

def main():
    """主函数"""
    print("=" * 60)
    print("文档整合工具 - 开始处理")
    print("=" * 60)

    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 获取所有文件夹
    folders = get_all_folders()
    print(f"\n找到 {len(folders)} 个文件夹需要处理")
    print(f"文件夹列表: {', '.join(folders)}")

    total_files = 0
    total_chars = 0

    for folder_name in folders:
        folder_path = os.path.join(BASE_DIR, folder_name)

        # 获取文件夹中的所有markdown文件
        md_files = []
        for item in os.listdir(folder_path):
            if item.endswith('.md'):
                filepath = os.path.join(folder_path, item)
                filesize = os.path.getsize(filepath)
                md_files.append((filepath, filesize))

        if not md_files:
            print(f"\n文件夹 {folder_name} 中没有markdown文件，跳过")
            continue

        # 合并文档
        merged_content, char_count = merge_documents(folder_name, md_files)

        # 写入输出文件
        output_file = os.path.join(OUTPUT_DIR, f"{folder_name}.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(merged_content)

        print(f"  输出文件: {output_file}")
        total_files += len(md_files)
        total_chars += char_count

    print("\n" + "=" * 60)
    print(f"整合完成!")
    print(f"  处理文件夹数: {len(folders)}")
    print(f"  处理文件数: {total_files}")
    print(f"  总字符数: {total_chars}")
    print(f"  输出目录: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()