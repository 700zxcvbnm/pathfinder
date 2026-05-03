from collections import Counter
from tqdm import tqdm
import random
import sqlite3

DB_PATH = "wiki.db"

#> config
MAX_DEPTH = 6
MAX_PATHS_PER_PAIR = 10
SAMPLES = 300

def get_neighbors(cur, title):
    cur.execute("SELECT dst FROM edges WHERE src = ?", (title,))
    return [row[0] for row in cur.fetchall()]

def find_paths(start, end):
    if start == end:
        return [[start]]

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    #each key is a visited node, and each value is
    #the list of all paths that reached it
    front = {start: [[start]]}
    back = {end: [[end]]}

    for depth in range(MAX_DEPTH):
        if not front or not back:
            break

        #prioritize the side with least leaves for efficiency
        if len(front) > len(back):
            front, back = back, front

        next_front = {}
        meeting_paths = []

        for node, paths in front.items():
            for neighbor in get_neighbors(cur, node):
                new_paths = [path + [neighbor] for path in paths]

                if neighbor not in next_front:
                    next_front[neighbor] = []
                next_front[neighbor].extend(new_paths)

                #check if this neighbor is in other side's leaves (path found)
                if neighbor in back:
                    for path_from_start in new_paths:
                        for path_from_end in back[neighbor]:
                            full = path_from_start + path_from_end[-2::-1]
                            meeting_paths.append(full)
                            if len(meeting_paths) >= MAX_PATHS_PER_PAIR:
                                con.close()
                                return meeting_paths

        #if we already found paths at this depth, just return
        if meeting_paths:
            con.close()
            return meeting_paths

        front = next_front

    con.close()
    return []

def get_random_articles(cur, n):
    cur.execute("SELECT MAX(rowid) FROM edges")
    max_id = cur.fetchone()[0]
    results = set()

    while len(results) < n:
        sample_id = random.randint(1, max_id)
        row = cur.execute(
            "SELECT src FROM edges WHERE rowid >= ? LIMIT 1", (sample_id,)
        ).fetchone()
        if row:
            results.add(row[0])

    return list(results)

con = sqlite3.connect(DB_PATH)
cur = con.cursor()
articles = get_random_articles(cur, SAMPLES * 2)
con.close()

pairs = [(articles[i*2], articles[i*2+1]) for i in range(min(SAMPLES, len(articles)//2))]

#find paths for all pairs
total_length = 0
found = 0
not_found = 0
node_counter = Counter()
length_counter = Counter()

for i, (start, end) in tqdm(enumerate(pairs), total=len(pairs)):
    paths = find_paths(start, end)
    if paths:
        length = len(paths[0]) - 1
        total_length += length
        found += 1
        length_counter[length] += 1

        #increment path nodes' visited count
        for path in paths[:MAX_PATHS_PER_PAIR]:
            for node in path[1:-1]:
                node_counter[node] += 1
    else:
        not_found += 1
        length_counter[0] += 1

print(f"> result")
print(f"pairs tried:     {len(pairs)}")
print(f"paths found:     {found}")
print(f"paths not found: {not_found}")
if found > 0:
    print(f"average length:  {total_length/found:.3f} degrees")

print(f"path length distribution:")
max_count = max(length_counter.values())
for length in sorted(length_counter):
    count = length_counter[length]
    bar   = '█' * int(count / max_count * 40)
    label = f"not found" if length == 0 else f"{length} degrees"
    print(f"  {label:12s} {bar} {count}")

print(f"top 20 centroid nodes:")
for node, count in node_counter.most_common(20):
    print(f"  {count:5d}x  {node}")