#!/usr/bin/env python3
import os
import glob

def count_lines(filepath):
    """Count lines in a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return sum(1 for line in f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0

def main():
    pidgin_dir = '/Users/ngl/code/pidgin/pidgin'
    files_over_200 = []
    
    # Find all Python files
    for root, dirs, files in os.walk(pidgin_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                line_count = count_lines(filepath)
                
                if line_count > 200:
                    # Get relative path from pidgin directory
                    rel_path = os.path.relpath(filepath, '/Users/ngl/code/pidgin')
                    files_over_200.append((line_count, rel_path))
    
    # Sort by line count (descending)
    files_over_200.sort(reverse=True)
    
    # Print results
    if files_over_200:
        print("Python files over 200 lines (sorted by size):")
        print("=" * 60)
        for count, path in files_over_200:
            print(f"{count:4d} lines: {path}")
    else:
        print("No Python files over 200 lines found!")

if __name__ == "__main__":
    main()