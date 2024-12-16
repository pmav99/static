from __future__ import annotations

import functools
import itertools
import math
import time
import typing as T

import bokeh.events
import geopandas as gpd
import holoviews as hv
import hvplot.pandas
import matplotlib.path as mpltPath
import matplotlib.pyplot as plt
import numpy as np
import numpy_indexed as npi
import pandas as pd
import panel as pn
import pyproj
import seareport_data as D
import shapely

np.random.default_rng(seed=42)

hv.extension("bokeh", inline=True)
pn.extension(throttled=True, inline=True, ready_notification="Ready")

hv.opts.defaults(
    # hv.opts.Overlay(
    #     #responsive=True,
    #     #show_grid=False,
    #     # tools=["hover", "crosshair", "undo"],
    #     # active_tools=["box_zoom"],
    # ),
    hv.opts.Polygons(
        tools=["hover", "crosshair", "undo"],
        active_tools=["box_zoom"],
        responsive=True,
        show_grid=False,
    ),
)

ICELAND = (-27, 62, -13, 68)
MEDITERRANEAN = (-7, 30, 45, 50)
SOUTH_POLE = (-180, -83, 180, -60)
SOUTH_POLE_PENINSULA = (-80, -75, -55, -60)
CRETE = (23.45, 34.5, 26.45, 36)

STEREO = pyproj.CRS("+proj=stere +lat_0=90 +lon_0=0 +ellps=sphere")
EPSG_4326 = pyproj.CRS(4326)


# GeoPandas functions
def F(series):
    return series.to_frame(name="geometry")

def G(geometry, crs):
    return gpd.GeoDataFrame(geometry=[geometry], crs=crs)

# Plot functions
def _handle_crs(gdf: gpd.GeoDataFrame, **kwargs: T.Any):
    if gdf.crs:
        if "crs" not in kwargs:
            kwargs["crs"] = gdf.crs
        if "projection" not in kwargs:
            kwargs["projection"] = gdf.crs
    return kwargs

def POLY(gdf: gpd.GeoDataFrame, **kwargs: T.Any):
    kwargs = _handle_crs(gdf, **kwargs)
    return gdf.hvplot.polygons(**kwargs)

def POINTS(gdf: gpd.GeoDataFrame, **kwargs: T.Any):
    kwargs = _handle_crs(gdf, **kwargs)
    return gdf.hvplot.points(**kwargs)

def PATH(gdf: gpd.GeoDataFrame, **kwargs: T.Any):
    kwargs = _handle_crs(gdf, **kwargs)
    return gdf.hvplot.paths(**kwargs)

def show(*objs, **kwargs) -> pn.io.server.StoppableThread | pn.io.server.Server:
    kwargs["threaded"] = kwargs.get("threaded", True)
    return pn.serve(pn.Column(*objs), **kwargs)

# main code
@functools.cache
def _get_transformer(from_crs: pyproj.CRS) -> pyproj.Transformer:
    transformer = pyproj.Transformer.from_crs(
        from_crs,
        EPSG_4326,
        always_xy=True,
        allow_ballpark=True,
        only_best=True,
    )
    return transformer


def measure_distance(plot, element):
    def dist(event):
        # Retrieve coords of previously clicked point and calculate distance
        px, py = pn.state.cache.get(event.model.id, (0, 0))
        cx, cy = event.x, event.y
        distance_cart = math.sqrt((cx - px)**2 + (cy - py)**2)
        # Store latest clicked point to cache
        pn.state.cache[event.model.id] = (cx, cy)
        # Transform coords to EPSG 4326 and calculdate distance on GEOID
        transformer = _get_transformer(plot.projection)
        px, py = transformer.transform(px, py)
        cx, cy = transformer.transform(cx, cy)
        _, _, distance_ellps = pyproj.Geod(ellps='WGS84').inv(px, py, cx, cy)
        # Show notification
        msg = f"Cartesian: {distance_cart:}\n"
        msg += f"Ellipsoid: {distance_ellps:}"
        print(msg)
        pn.state.notifications.info(msg, duration=15000)

    # Register callback
    plot.state.on_event(bokeh.events.Tap, dist)


if __name__ == "__main__":
    osm_land = gpd.read_file("/home/panos/Prog/poseidon/coastlines/raw/osm/land-polygons-complete-4326/land_polygons.shp", engine="pyogrio")
    crete = osm_land.clip(CRETE)
    crete_stereo = crete.to_crs(STEREO)
    #
    buffer_size = 100
    crete_stereo_buffered = F(G(crete_stereo.buffer(buffer_size).union_all(), crs=STEREO).make_valid().explode().exterior.polygonize())
    plot = hv.Overlay([
        POLY(crete_stereo, alpha=0.2),
        POLY(crete_stereo_buffered, alpha=0.4),
    ]).opts(hooks=[measure_distance], title="OSM - Crete - 100m buffer")
    hv.save(plot, "osm_crete_100m_buffer.html", backend="bokeh")

