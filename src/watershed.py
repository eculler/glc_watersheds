import fiona, fiona.crs
import geopandas as gpd
import shapely.geometry
import shapely.speedups
import pandas as pd
import matplotlib.pyplot as plt
import os
import pyproj

out_fn = 'out/watersheds.csv'
gagesii_path = 'data/GAGESII/CONUS/bas_all_us.shp'
slide_path = 'data/SLIDE_NASA_GLC/GLC20180821.csv'
slide_id_path = 'Landslide_ID_Data.csv'

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

    if row.location_accuracy in ['exact', 'unknown']:
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
    slide_df = pd.read_csv(slide_path)
    slide = gpd.GeoDataFrame(
        slide_df.drop(['Longitude', 'Latitude'], axis=1),
        crs=latlon_crs,
        geometry = [
            shapely.geometry.Point(xy)
            for xy in zip(slide_df.longitude, slide_df.latitude)])
    id_df = pd.read_csv(slide_id_path, index_col='ID')
    slide = slide.join(id_df, how='right')
    print(slide)

    # Load basin data
    gagesii = gpd.read_file(gagesii_path, bbox=bbox)
    gagesii['GAGE_ID'] = pd.to_numeric(gagesii['GAGE_ID'])

    # Filter basins with active record
    # (skip this before downloading discharge records)
    # active = pd.read_csv('data/gages_active.txt', index_col='site_no')
    # gagesii = gagesii.join(active, on='GAGE_ID', how='inner')

    # Match projections
    slide = slide.to_crs(gagesii.crs)

    # Buffer landslide locations
    slide['geometry'] = slide.apply(buffer_slide, axis=1)

    # Find basins overlapping the buffer
    watersheds = gpd.overlay(slide, gagesii, how='intersection')

    # Remove nested watersheds
    watersheds = watersheds.groupby('ID').apply(remove_nested)

    # Save results
    pd.DataFrame(watersheds).to_csv(
        out_fn, columns=['ID', 'GAGE_ID'], index=False)
