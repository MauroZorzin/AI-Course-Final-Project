import os
import json
import shutil

BAD_QUERIES = {
    'natural': set(),
    'abstract': set(),
    'counterfactual': set()
}

def load_bad_queries():
    base_paths = [os.path.join('sources', 'queries'), os.path.join('..', 'sources', 'queries')]
    queries_dir = None
    for p in base_paths:
        if os.path.exists(p):
            queries_dir = p
            break
            
    if not queries_dir:
        print("Warning: Could not find 'sources/queries' directory. Skipping bad query detection.")
        return

    for variant in ['natural', 'abstract', 'counterfactual']:
        path = os.path.join(queries_dir, f"{variant}.jsonl")
        if not os.path.exists(path):
            continue
        
        print(f"Loading queries from {path} for variant '{variant}'...")
        count_bad = 0
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        q = json.loads(line)
                        q_id = q.get('id')
                        
                        gold_answers_raw = q.get("gold_answers")
                        if not gold_answers_raw:
                             val = q.get("answer") or q.get("gold_answer")
                             if val:
                                 gold_answers_raw = [val] if not isinstance(val, list) else val
                        
                        gold_path = q.get('gold_path', [])
                        evidence = q.get('evidence_triples', [])
                        
                        if not gold_path or not gold_answers_raw or not evidence:
                            continue
                            
                        # Target is the object of the last triple in gold path
                        target_answer = gold_path[-1][2] 
                        
                        # Other valid answers
                        all_answers = set(str(x) for x in gold_answers_raw)
                        others = all_answers - {target_answer}
                        
                        if not others:
                            continue
                            
                        # Check leak
                        for tri in evidence:
                            if tri[2] in others:
                                BAD_QUERIES.setdefault(variant, set()).add(q_id)
                                count_bad += 1
                                break
                    except Exception:
                        pass
            print(f"  -> Found {count_bad} queries with leaked answers.")
        except Exception as e:
            print(f"Error reading {path}: {e}")

def merge_partials(dirpath, base_filename):
    """
    Merges any found partial files (base_filename + '.part_*') into base_filename.
    Removes partial files after successful merge.
    """
    # Find all partials for this base file
    prefix = base_filename + ".part_"
    partials = []
    try:
        if os.path.exists(dirpath):
            partials = [f for f in os.listdir(dirpath) if f.startswith(prefix)]
    except OSError:
        pass
        
    if not partials:
        return

    print(f"Merging {len(partials)} partial files into {base_filename} in {dirpath}...")
    base_path = os.path.join(dirpath, base_filename)
    
    # Open base file in append mode (creates if not exists)
    try:
        with open(base_path, 'a', encoding='utf-8') as outfile:
            for p in partials:
                p_path = os.path.join(dirpath, p)
                try:
                    with open(p_path, 'r', encoding='utf-8') as infile:
                        shutil.copyfileobj(infile, outfile)
                        # Ensure we end with a newline if missing (optional but safe)
                        # Note: This might add extra newlines if the partial already ends with one,
                        # but empty lines are handled/ignored by clean_file.
                        outfile.write('\n')
                    
                    # Remove partial after merge
                    os.remove(p_path)
                except Exception as e:
                    print(f"Error merging {p}: {e}")
    except Exception as e:
        print(f"Error opening {base_path} for merging: {e}")

def clean_file(filepath):
    valid_lines = []
    removed_count = 0
    bad_query_count = 0
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
                    is_bad = False
                    
                    # 1. Check errors
                    if data.get('error') or data.get('parse_error'):
                        is_bad = True
                        
                    # 2. Check bad query (multiple answers leaked)
                    if not is_bad:
                        variant = data.get('graph_variant')
                        qid = data.get('query_id')
                        if variant and qid:
                            # Handle potential casing or missing keys
                            bad_set = BAD_QUERIES.get(variant)
                            if bad_set and qid in bad_set:
                                is_bad = True
                                bad_query_count += 1
                    
                    if is_bad:
                        removed_count += 1
                    else:
                        valid_lines.append(line)
                except json.JSONDecodeError:
                    removed_count += 1
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    if removed_count > 0:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for line in valid_lines:
                    f.write(line + '\n')
            print(f"Cleaned {filepath}: Removed {removed_count} lines ({bad_query_count} due to leak) out of {total_count}.")
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")
    else:
        print(f"Checked {filepath}: No errors found.")

def main():
    root_dir = 'out' 
    
    # Pre-load bad queries
    load_bad_queries()
    
    if not os.path.exists(root_dir):
        print(f"Directory '{root_dir}' not found in current directory: {os.getcwd()}")
        return

    print(f"Scanning '{root_dir}' for responses.jsonl and partial files...")
    files_found = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Identify "base" files (targets)
        # A target is any 'response(s).jsonl' file, OR a file implied by the existence of 'response(s).jsonl.part_*'
        candidates = set()
        for file in filenames:
            if file.startswith('responses.jsonl') or file.startswith('response.jsonl'):
                if '.part_' in file:
                    # e.g. response.jsonl.part_0 -> base is response.jsonl
                    base = file.split('.part_')[0]
                    candidates.add(base)
                else:
                    candidates.add(file)
        
        for base_file in candidates:
            files_found += 1
            # 1. Merge partials into the base file (if any)
            merge_partials(dirpath, base_file)
            
            # 2. Clean the resulting file
            clean_file(os.path.join(dirpath, base_file))
    
    print(f"Processing complete. Processed {files_found} response files (and their partials).")

if __name__ == '__main__':
    main()
