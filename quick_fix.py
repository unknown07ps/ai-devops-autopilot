#!/usr/bin/env python3
"""
Diagnostic script to find all SELECT 1 issues in the codebase
"""

import os
import re

def find_select_issues(file_path):
    """Find all problematic SELECT 1 patterns"""
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"\n📁 Analyzing: {file_path}")
    print("="*70)
    
    # Check for text import
    has_text_import = False
    for i, line in enumerate(lines, 1):
        if 'from sqlalchemy import text' in line:
            has_text_import = True
            print(f"✅ Line {i}: text import found")
            break
    
    if not has_text_import:
        print("❌ MISSING: 'from sqlalchemy import text' import")
        print("   Add this near line 30-40 with other SQLAlchemy imports")
    
    print()
    
    # Find all SELECT 1 patterns
    patterns = [
        (r'\.execute\(\s*"SELECT 1"\s*\)', 'Naked SELECT 1 with double quotes'),
        (r"\.execute\(\s*'SELECT 1'\s*\)", 'Naked SELECT 1 with single quotes'),
        (r'\.execute\(\s*text\(\s*["\']SELECT 1["\']\s*\)\s*\)', 'Already fixed (has text())'),
    ]
    
    issues_found = []
    fixed_lines = []
    
    for i, line in enumerate(lines, 1):
        for pattern, description in patterns:
            if re.search(pattern, line):
                if 'text(' in line:
                    fixed_lines.append((i, line.strip(), description))
                else:
                    issues_found.append((i, line.strip(), description))
    
    if issues_found:
        print("❌ ISSUES FOUND:")
        print("-"*70)
        for line_num, line_content, desc in issues_found:
            print(f"Line {line_num}: {desc}")
            print(f"  → {line_content}")
            print()
    else:
        print("✅ No naked SELECT 1 issues found")
    
    if fixed_lines:
        print("\n✅ ALREADY FIXED:")
        print("-"*70)
        for line_num, line_content, desc in fixed_lines:
            print(f"Line {line_num}: {desc}")
            print(f"  → {line_content}")
    
    print("\n" + "="*70)
    print(f"Summary: {len(issues_found)} issues, {len(fixed_lines)} already fixed")
    print("="*70)
    
    return len(issues_found) == 0 and has_text_import

def auto_fix_file(file_path):
    """Automatically fix all issues"""
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"\n🔧 Attempting to fix {file_path}...")
    
    # Backup first
    backup_path = f"{file_path}.backup"
    with open(file_path, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original_content)
    print(f"✅ Backup created: {backup_path}")
    
    content = original_content
    fixes_applied = 0
    
    # Fix 1: Add text import if missing
    if 'from sqlalchemy import text' not in content:
        print("🔧 Adding text import...")
        # Find a good place to insert it
        if 'from sqlalchemy.orm import Session' in content:
            content = content.replace(
                'from sqlalchemy.orm import Session',
                'from sqlalchemy import text\nfrom sqlalchemy.orm import Session'
            )
        elif 'from sqlalchemy' in content:
            # Add after first sqlalchemy import
            content = re.sub(
                r'(from sqlalchemy[^\n]+\n)',
                r'\1from sqlalchemy import text\n',
                content,
                count=1
            )
        fixes_applied += 1
    
    # Fix 2: Wrap all naked SELECT 1 in text()
    patterns_to_fix = [
        (r'\.execute\(\s*"SELECT 1"\s*\)', '.execute(text("SELECT 1"))'),
        (r"\.execute\(\s*'SELECT 1'\s*\)", ".execute(text('SELECT 1'))"),
    ]
    
    for pattern, replacement in patterns_to_fix:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            fixes_applied += len(matches)
            print(f"🔧 Fixed {len(matches)} occurrence(s) of pattern: {pattern}")
    
    # Write fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ Applied {fixes_applied} fixes to {file_path}")
    print(f"💡 To restore original: cp {backup_path} {file_path}")
    
    return True

def main():
    print("="*70)
    print("SQLAlchemy 2.0 Compatibility Diagnostic Tool")
    print("="*70)
    
    file_path = "src/main.py"
    
    # First, diagnose
    is_clean = find_select_issues(file_path)
    
    if not is_clean:
        print("\n" + "="*70)
        response = input("\n🔧 Apply automatic fixes? (yes/no): ").strip().lower()
        
        if response in ['yes', 'y']:
            if auto_fix_file(file_path):
                print("\n✅ Fixes applied! Now:")
                print("   1. Restart your FastAPI server")
                print("   2. Run: python test_health.py")
                print("   3. Run: python test_integrity.py")
        else:
            print("\n📝 Manual fix required. Look for the issues listed above.")
    else:
        print("\n✅ All checks passed! File is clean.")
        print("\nIf you're still seeing errors, try:")
        print("   1. Restart your FastAPI server")
        print("   2. Check if there are other Python files importing main.py")
        print("   3. Clear any Python cache: rm -rf __pycache__ src/__pycache__")

if __name__ == "__main__":
    main()