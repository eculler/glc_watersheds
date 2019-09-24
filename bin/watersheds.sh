docker build --tag wshds .
docker run --rm -i \
  -v ~/Documents/landslide/data/SLIDE_NASA_GLC:/wshds/data/SLIDE_NASA_GLC \
  -v /Volumes/LabShare/GAGESII_reorganize:/wshds/data/GAGESII \
  -v ~/Documents/landslide/glc_watersheds/results:/wshds/out \
  -v ~/Documents/landslide/glc_watersheds/data:/wshds/data \
  -t wshds:latest \
  conda run -n wshdsenv python src/watersheds.py
