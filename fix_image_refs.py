#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片引用修复脚本 - 修复markdown图片引用格式
"""

import os
import re

BASE_DIR = r"C:\Users\Administrator\DocProjects\mianshi"
OUTPUT_DIR = os.path.join(BASE_DIR, "000最终版000")

def fix_image_references(content):
    """修复图片引用格式"""
    # 修复格式：[filename.png] -> ![filename](images/filename.png)
    # 匹配 [filename.png] 格式（没有 ! 前缀）
    def replace_image_ref(match):
        old_ref = match.group(0)
        filename = match.group(1)
        
        # 跳过已经是正确格式的引用
        if old_ref.startswith('!['):
            return old_ref
        
        # 转换为正确的图片引用格式
        return f"![{filename}](images/{filename})"
    
    # 匹配 [filename.png] 格式（没有 ! 前缀）
    # 使用负向前瞻来排除链接格式
    content = re.sub(r'\[([a-zA-Z0-9_\-]+\.(?:png|jpg|jpeg|gif|webp|bmp|svg))\](?!\()', replace_image_ref, content)
    
    return content

def main():
    print("=" * 60)
    print("图片引用修复工具")
    print("=" * 60)
    
    total_files = 0
    total_fixes = 0
    
    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith('.md'):
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复图片引用
            new_content = fix_image_references(content)
            
            # 统计修复的图片引用数量
            # 计算修复前的图片引用数量
            before_count = len(re.findall(r'\[([a-zA-Z0-9_\-]+\.(?:png|jpg|jpeg|gif|webp|bmp|svg))\](?!\()', content))
            
            # 计算修复后的图片引用数量
            after_count = len(re.findall(r'!\[([a-zA-Z0-9_\-]+\.(?:png|jpg|jpeg|gif|webp|bmp|svg))\]\(images/[a-zA-Z0-9_\-]+\.(?:png|jpg|jpeg|gif|webp|bmp|svg)\)', new_content))
            
            fixes = after_count - before_count
            
            if fixes > 0:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"  {filename}: 修复 {fixes} 个图片引用")
                total_fixes += fixes
            else:
                print(f"  {filename}: 无需修复 (before={before_count}, after={after_count})")
            
            total_files += 1
    
    print(f"\n处理完成: {total_files} 个文件, 修复 {total_fixes} 个图片引用")

if __name__ == "__main__":
    main()
