import xarray as xr
import holoviews as hv
import hvplot.pandas

ds = xr.open_dataset("/home/panos/Downloads/stofs_2d_glo.t06z.points.cwl.nc")
df = ds[["x", "y", "station_name"]].to_pandas()
df = df.assign(station_name=df.station_name.str.decode("utf-8"))
df = df.assign(is_satellite=df.station_name.str.startswith("UJ").astype(bool))
plot = df.hvplot.points(
    geo=True,
    tiles=True,
    hover_cols=["x", "y", "station_name", "is_satellite"],
    legend=True,
    color="is_satellite",
    cmap="colorblind",
    color_levels=2,
    responsive=True,
    height=900,
)
hv.save(plot, "stofs2d_stations.html", backend="bokeh")
