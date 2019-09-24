import fiona, fiona.crs
import geopandas as gpd
import shapely.geometry
import shapely.speedups
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import pyproj

out_fn = 'out/watersheds.csv'
gagesii_path = 'data/GAGESII/CONUS/bas_all_us.shp'
active_gages_path = None
slide_path = 'data/Global_Landslide_Catalog_Export.csv'
slide_id_path = 'data/Landslide_ID_Data.csv'

latlon_crs = {'init': 'epsg:4326'}

def buffer_slide(row):
    """
    Compute a buffer the size of the location accuracy
    around the landslide location

    Parameters:
    ----------
    row : geopandas.GeoDataFrame
        GeoDataFrame row containing information about landslide
        location and location accuracy

    Returns:
    --------
    geopandas.GeoDataFrame
        GeoDataFrame with the geometry changed to a circular
        error buffer around the location
    """

    if row.location_accuracy in ['exact', 'unknown', np.nan]:
        return row.geometry.buffer(1)
    # Convert km to m
    radius = int(row.location_accuracy[:-2]) * 1000

    return row.geometry.buffer(radius)


def remove_nested(group):
    """
    Removes watersheds that entirely contain another
    watershed and do not cover any more of the
    landslide buffer from the list of possible
    watersheds

    Parameters:
    -----------
    group : geopandas.GeoDataFrame
        a geodataframe of watersheds

    Returns:
    --------
    geopandas.GeoDataFrame
        The reduced geodataframe of watersheds
    """

    done = []
    keep = []

    # Start with the smallest watershed
    inds = group.sort_values('AREA', ascending=False).index
    for i in inds[:-1]:
        # Does the watershed intersect with any smaller watersheds?
        intersection = gpd.overlay(
            group.loc[[i]], group.drop([i] + done), how='intersection')
        if intersection.empty:
            # If not, keep it
            keep.append(i)
        else:
            # If so, does the landslide buffer extend beyond the
            # smaller watershed?
            diff = group.at[i, 'geometry'].difference(intersection.unary_union)
            if diff:
                # If so, keep the larger one anyway
                keep.append(i)

        done.append(i)

    # Include smallest watershed
    keep.append(inds[-1])

    return group.loc[keep]


if __name__== '__main__':
    # Check that the output directory exists before running
    if not os.path.exists(os.path.dirname(out_fn)):
        raise FileNotFoundError(
            'Directory does not exist: {}'.format(out_fn))

    # Speed up set operations
    shapely.speedups.enable()

    # Load landslide data
    slide = pd.read_csv(slide_path, index_col='event_id')
    slide_id = pd.read_csv(slide_id_path, index_col='ID')
    slide = slide.join(slide_id, how='right')

    # Get the study extent to speed up gages II loading
    bbox = gpd.GeoDataFrame(
        pd.DataFrame(),
        geometry=[shapely.geometry.box(
            slide.longitude.min(), slide.latitude.min(),
            slide.longitude.max(), slide.latitude.max())],
        crs = latlon_crs)

    # Convert landslides to a GeoDataFrame
    slide = gpd.GeoDataFrame(
        slide.drop(['longitude', 'latitude'], axis=1),
        crs=latlon_crs,
        geometry = [
            shapely.geometry.Point(xy)
            for xy in zip(slide.longitude, slide.latitude)])

    # Load basin data
    gagesii = gpd.read_file(gagesii_path, bbox=bbox)
    gagesii['GAGE_ID'] = pd.to_numeric(gagesii['GAGE_ID'])

    # Filter basins with active record
    if active_gages_path:
        # (skip this before downloading discharge records)
        active = pd.read_csv(active_gages_path, index_col='site_no')
        gagesii = gagesii.join(active, on='GAGE_ID', how='inner')

    # Match landslide and basin projections
    slide = slide.to_crs(gagesii.crs)

    # Buffer landslide locations
    slide['geometry'] = slide.apply(buffer_slide, axis=1)

    # Keep slide id
    slide['event_id'] = slide.index

    # Find basins overlapping the buffer
    watersheds = gpd.overlay(slide, gagesii, how='intersection')

    # Remove nested watersheds
    watersheds = watersheds.groupby('event_id').apply(remove_nested)

    # Save results
    pd.DataFrame(watersheds).to_csv(
        out_fn, columns=['event_id', 'GAGE_ID'], index=False)
