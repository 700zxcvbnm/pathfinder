from tqdm import tqdm
import sqlite3
import json

DB_PATH = "wiki.db"
OUTPUT  = "path_result.json"

#> config
#note: just copy article title, not the one inside url
START = "67"
END   = "Gay"
MAX_DEPTH = 6 #default: 6
MAX_PATHS = 20

def get_neighbors(cur, title):
    cur.execute("SELECT dst FROM edges WHERE src = ?", (title,))
    return [row[0] for row in cur.fetchall()]

def get_reverse_neighbors(cur, title):
    cur.execute("SELECT src FROM edges WHERE dst = ?", (title,))
    return [row[0] for row in cur.fetchall()]

def find_paths(start, end):
    if start == end:
        return [[start]]

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    front = {start: [[start]]}
    back  = {end:   [[end]]}
    front_is_forward = True  # track which direction front is expanding in

    for depth in range(MAX_DEPTH):
        if not front or not back:
            break

        if len(front) > len(back):
            front, back = back, front
            front_is_forward = not front_is_forward

        next_front = {}
        meeting_paths = []

        for node, paths in front.items():
            # use correct direction based on which side we're expanding
            neighbors = get_neighbors(cur, node) if front_is_forward \
                       else get_reverse_neighbors(cur, node)

            for neighbor in neighbors:
                new_paths = [path + [neighbor] for path in paths]

                if neighbor not in next_front:
                    next_front[neighbor] = []
                next_front[neighbor].extend(new_paths)

                if neighbor in back:
                    for path_from_start in new_paths:
                        for path_from_end in back[neighbor]:
                            # if front is forward: front + reverse(back)
                            # if front is backward: reverse(front) + back
                            if front_is_forward:
                                full = path_from_start + path_from_end[-2::-1]
                            else:
                                full = path_from_end + path_from_start[-2::-1]
                            meeting_paths.append(full)
                            if len(meeting_paths) >= MAX_PATHS:
                                con.close()
                                return meeting_paths

        if meeting_paths:
            con.close()
            return meeting_paths

        front = next_front

    con.close()
    return []

print(f"finding: {START} -> {END}")

paths = find_paths(START, END)

if paths is None:
    print(f"no path found within {MAX_DEPTH} hops lmao")
else:
    print(f"found {len(paths)} paths of length {len(paths[0])-1}:")
    for path in paths:
      print(path)

    result = {
        "start": START,
        "end": END,
        "degrees": len(paths[0]) - 1,
        "paths": paths
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    print(f"saved to {OUTPUT}")