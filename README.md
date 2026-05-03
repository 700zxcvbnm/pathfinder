# pathfinder
this project was originally developed on Google Colab, this is just a github port.
colab project link: https://colab.research.google.com/drive/1gnqadPP1BNgXh9v9uvLmAs7R3R8gCACc?usp=sharing

## code
### [0] initialization (`init.py`)
the compressed wiki database's quite large (~11 gb which compresses to ~60gb) so you'll need around 10 minutes to initialize

### [1] find paths (`find_paths.py`)
edit the START and END variables
on default will only search 6 depths, where querying every leaf on a side counts as 1 depth
if a path is found, it'll find other paths with same length up to MAX_PATHS

### [2] display graph in ngrok (`web_viewer.py`)
renders graph viewer from path_result.json
you'll need to execute the code block again if you updated the json

*NOTE: the front-end is made by AI.*

### [miscellaneous] find average path length & "center" of wikipedia (`analyze.py`)
analysis for final result presentation

## result
average path length: 2.967 (sample size: 300)
![https://hackmd.io/_uploads/Hy2wSU65bx.png]()

the "center" of wikipedia: United States (sample size: 300)
![https://hackmd.io/_uploads/Syi0S869Wg.png]()
(center as in the page that's been visited the most in all paths)

## note
we fixed an old issue where the code claims "article A links to B" even though theres no hyperlink to B.
in hindsight, we implemented the bidirectional BFS wrong. we accidentally made the two sides of the paths face each other:
```
A (front) -> 1 -> 2 -> 3 <- 4 <- B (back)
```
in reality, it should've been:
```
A (front) -> 1 -> 2 -> 3 -> 4 -> B (back)
```
when we iterate from the back side, we should switch to reverse lookups to preserve the forward direction.