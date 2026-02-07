import os
import json

def clean_file(filepath):
    valid_lines = []
    removed_count = 0
    total_count = 0
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                total_count += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Check for error or parse_error. 
                    # If field is present and not None/empty, it's considered an error.
                    if data.get('error') or data.get('parse_error'):
                        removed_count += 1
                    else:
                        valid_lines.append(line)
                except json.JSONDecodeError:
                    # If it's not valid JSON, treat as error/corrupted
                    removed_count += 1
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    if removed_count > 0:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for line in valid_lines:
                    f.write(line + '\n')
            print(f"Cleaned {filepath}: Removed {removed_count} lines out of {total_count}.")
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")
    else:
        print(f"Checked {filepath}: No errors found.")

def main():
    # Use absolute path to be safe, or relative to cwd. 
    # Provided context shows we are in workspace root.
    root_dir = 'out' 
    
    if not os.path.exists(root_dir):
        print(f"Directory '{root_dir}' not found in current directory: {os.getcwd()}")
        return

    print(f"Scanning '{root_dir}' for responses.jsonl files...")
    files_found = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            if file == 'responses.jsonl':
                files_found += 1
                clean_file(os.path.join(dirpath, file))
    
    print(f"Processing complete. Found {files_found} 'responses.jsonl' files.")

if __name__ == '__main__':
    main()
