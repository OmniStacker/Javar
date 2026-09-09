#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
来源标注移除脚本 - 移除文档中的来源引用语句
"""

import os
import re

BASE_DIR = r"C:\Users\Administrator\DocProjects\mianshi"
OUTPUT_DIR = os.path.join(BASE_DIR, "000最终版000")

def remove_source_markers(content):
    """移除来源标注"""
    # 匹配来源标注模式
    # 格式：## 来源: xxx.md\r?\n---\r?\n# xxx（可能包含BOM字符）
    pattern = r'## 来源: (.+\.md)\r?\n---\r?\n[\ufeff]*#[^\r\n]+\r?\n'
    
    def replace_source_marker(match):
        # 从来源文件名提取标题文本
        source_line = match.group(1)
        title_text = source_line.replace('.md', '')
        
        return "\n# " + title_text + "\n"
    
    content = re.sub(pattern, replace_source_marker, content)
    
    return content

def remove_document_notice(content):
    """移除文档来源声明"""
    # 匹配整行：本文档由多个来源整合而成，保留原始内容的完整性。（可能带 > 引用符号）
    pattern = r'^\s*>\s*本文档由多个来源整合而成，保留原始内容的完整性。\r?\n'
    
    content = re.sub(pattern, '', content, flags=re.MULTILINE)
    
    return content

def main():
    print("=" * 60)
    print("来源标注移除工具")
    print("=" * 60)
    
    total_files = 0
    total_sources = 0
    total_notices = 0
    
    for filename in os.listdir(OUTPUT_DIR):
        if filename.endswith('.md'):
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 统计移除的来源标注数量
            before_sources = len(re.findall(r'## 来源: .+\.md', content))
            
            # 统计文档来源声明数量
            before_notices = len(re.findall(r'本文档由多个来源整合而成，保留原始内容的完整性。', content))
            
            # 移除来源标注
            new_content = remove_source_markers(content)
            
            # 移除文档来源声明
            new_content = remove_document_notice(new_content)
            
            # 统计移除后的来源标注数量
            after_sources = len(re.findall(r'## 来源: .+\.md', new_content))
            
            # 统计移除后的文档来源声明数量
            after_notices = len(re.findall(r'本文档由多个来源整合而成，保留原始内容的完整性。', new_content))
            
            removed_sources = before_sources - after_sources
            removed_notices = before_notices - after_notices
            
            if removed_sources > 0 or removed_notices > 0:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                if removed_sources > 0:
                    print(f"  {filename}: 移除 {removed_sources} 个来源标注")
                    total_sources += removed_sources
                if removed_notices > 0:
                    print(f"  {filename}: 移除文档来源声明")
                    total_notices += 1
            
            total_files += 1
    
    print(f"\n处理完成: {total_files} 个文件")
    print(f"  来源标注: {total_sources} 个")
    print(f"  文档来源声明: {total_notices} 个文件")

if __name__ == "__main__":
    main()
