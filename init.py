!pip install pyngrok tqdm gdown -q
!apt-get install -y zstd -q

!gdown 1IqxiN1OJa95H5_9pYlv5H6ea98xt6KiM
!zstd -d wiki.db.zst -o wiki.db