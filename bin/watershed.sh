docker build --tag wshds .
docker run --rm -i \
  -v ~/Documents/landslide/data/SLIDE_NASA_GLC:/gis/data/SLIDE_NASA_GLC \
  -v /Volumes/LabShare/GAGESII_reorganize:/gis/data/GAGESII \
  -v ~/Documents/landslide/watersheds_for_Andrew/results:/gis/out \
  -t wshds:latest \
  python3 src/watershed.py
