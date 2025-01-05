# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
  

from urllib.error import URLError
from urllib.request import urlopen
import zipfile
from io import BytesIO
import json
import requests
import pandas as pd
from numpy import linalg
import matplotlib.pyplot as plt
import matplotlib
import shapely

import geopandas as gpd
import folium
import contextily
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import h3 as h3
from geojson import Feature, Point, FeatureCollection
from shapely.geometry import shape

import streamlit as st
from streamlit.hello.utils import show_code
from streamlit_folium import folium_static

def get_businesses(location, term, api_key):
    """
    Uses YelpAPI to pull up to 1000 businesses, Lat/Lon, Avg Rating, and   
    Number of Ratings (plus distance, but we aren't using that).  

    """
    headers = {'Authorization': 'Bearer %s' % api_key}
    url = 'https://api.yelp.com/v3/businesses/search'

    data = [] 
    for offset in range(0, 100, 50): # Changed to 100 to limit API rate-limiting
        params = {
            'limit': 50, 
            'location': location.replace(' ', '+'),
            'term': term.replace(' ', '+'),
            'offset': offset
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data += response.json()['businesses']
        elif response.status_code == 400:
            print('400 Bad Request')
            break

    result_df = pd.DataFrame({'Name': [], 'Lat': [], 'Lon':[], 'Rating':[], 'RatingCount':[], 'Distance':[]})
    listdic = []
    for result in data:
        name = result['name']
        lat = result['coordinates']['latitude']
        lon = result['coordinates']['longitude']
        rating = result['rating']
        ratingcount = result['review_count']
        distance = result['distance']
        listdic=pd.Series([name,lat,lon,rating,ratingcount,distance], index=['Name', 'Lat','Lon', 'Rating', 'RatingCount', 'Distance'])
        result_df=pd.concat([result_df, listdic.to_frame().T], ignore_index=True)

    return result_df


def MapYelps(df):
  #Set figure size, then add map to that
  f = folium.Figure(width=800, height=400)
  m=folium.Map(tiles='CartoDB positron', control=False).add_to(f) 
  
  #Pull top left, bottom right corners and set map bound box. 
  sw = [df.Lat.min(), df.Lon.min()]
  ne = [df.Lat.max(), df.Lon.max()]
  m.fit_bounds([sw,ne])

  #Create a layer, add points to it, then add the layer to your map
  Locations = folium.FeatureGroup(name = "Locations")
  for index, row in df.iterrows():
    html = '''
    <b>Name:</b> {name} <br>
    <b>Rating:</b> {rating}
    '''.format(name = row.Name, rating=row.Rating)

    iframe = folium.IFrame(html)
    popup = folium.Popup(iframe,
                        min_width=200,
                        max_width=120)

    Locations.add_child(folium.Marker(location=[row.Lat,row.Lon], popup = popup))
  m.add_child(Locations)
  
  #Add ability to turn off/on your layers
  folium.LayerControl().add_to(m)
  
  return(st_folium(m, width=700, height=450))


def Hexify(df, resolution=7):
  """
  Hexify will just add a column to the input df that gives the HEX ID for each point in the dataset.
  DF must include columns "Lat" and "Lon". 
  """
  hex_ids = df.apply(lambda row: h3.geo_to_h3(row.Lat, row.Lon, resolution), axis = 1)
  df_result = df.assign(hex_id=hex_ids.values)
  return df_result


def hex_df_to_geojson(df_hex, column_name = "value"):
    """
    Produce the GeoJSON for a dataframe, constructing the geometry from the "hex_id" column
    and with a property matching the one in column_name
    """    
    list_features = []
    
    for i,row in df_hex.iterrows():
        try:
            geometry_for_row = { "type" : "Polygon", "coordinates": [h3.h3_to_geo_boundary(h=row["hex_id"],geo_json=True)]}
            feature = Feature(geometry = geometry_for_row , id=row["hex_id"], properties = {column_name : row[column_name]})
            list_features.append(feature)
        except:
            print("An exception occurred for hex " + row["hex_id"]) 

    feat_collection = FeatureCollection(list_features)
    geojson_result = json.dumps(feat_collection)
    return geojson_result

def get_color(custom_cm, val, vmin, vmax):
    """
    Scales the color gradient to your specific data range
    """
    return matplotlib.colors.to_hex(custom_cm((val-vmin)/(vmax-vmin)))

def choropleth_map(df_aggreg, column_name = "value", border_color = 'black', fill_opacity = 0.7, color_map_name = "Blues", initial_map = None, zoom=7):  
    """
    This is a somewhat complicated route to creating a choropleth only lightly edited from online.  
    Below, I use Folium's built-in choropleth capabilities, and I believe it's much simpler to understand. 
    """
    #colormap
    min_value = df_aggreg[column_name].min()
    max_value = df_aggreg[column_name].max()
    mean_value = df_aggreg[column_name].mean()
    print(f"Colour column min value {min_value}, max value {max_value}, mean value {mean_value}")
    print(f"Hexagon cell count: {df_aggreg['hex_id'].nunique()}")

    # the name of the layer just needs to be unique, put something silly there for now:
    name_layer = "Choropleth " + str(df_aggreg)

    if initial_map is None:
        initial_map = folium.Map(location= [+39.9698749,	-083.0090858], zoom_start=zoom, tiles="cartodbpositron")

    #create geojson data from dataframe
    geojson_data = hex_df_to_geojson(df_hex = df_aggreg, column_name = column_name)

    # color_map_name 'Blues' for now, many more at https://matplotlib.org/stable/tutorials/colors/colormaps.html to choose from!
    custom_cm = matplotlib.cm.get_cmap(color_map_name)

    folium.GeoJson(
        geojson_data,
        style_function=lambda feature: {
            'fillColor': get_color(custom_cm, feature['properties'][column_name], vmin=min_value, vmax=max_value),
            'color': border_color,
            'weight': 1,
            'fillOpacity': fill_opacity 
        }, 
        name = name_layer
    ).add_to(initial_map)

    return initial_map

myzip = zipfile.ZipFile(BytesIO(urlopen("https://www2.census.gov/geo/tiger/TIGER2022/COUNTY/tl_2022_us_county.zip").read()))


myzip.extractall(path='files/')

usa = gpd.read_file(r'files/tl_2022_us_county.shp')



def poly_geojson(poly):
  poly_geojson = gpd.GeoSeries(poly).__geo_interface__
  poly_geojson = poly_geojson['features'][0]['geometry'] 
  return poly_geojson


def MapYelps_allinone(df, markers = True, HexHeat = 'Hex', res = 8, zoom = 9, fillGeom=False):
  """
  df should be data frame containing at least columns named Lat and Lon. For Markers, want "Name" and "Rating" too. 
  HexHeat should be set to 'Hex' or 'Heat'. Any other value will not return a layer.
  res determines size of hexagons. 8 is a good starting point for county-level work.
  zoom is the starting zoom level *if* you are not using markers = True. If using markers = True, then it will use a boundary box based on marker locations. 
  fillGeom: When HexHeat=Hex, this determines whether you fill an outer polygon with ALL polygons. Use 5-digit state+county FIPS code or 2-digit state code. 
  """  
  if 'map' not in st.session_state or st.session_state.map is None:
    f = folium.Figure(width=800, height=400)

    if (markers==True):
      m=folium.Map(tiles='CartoDB positron', control=False).add_to(f)
      sw = [df.Lat.min(), df.Lon.min()]
      ne = [df.Lat.max(), df.Lon.max()]
      m.fit_bounds([sw,ne])
      Locations = folium.FeatureGroup(name = "Locations")

      for index, row in df.iterrows():
        html = '''
        <b>Name:</b> {name} <br>
        <b>Rating:</b> {rating}
        '''.format(name = row.Name, rating=row.Rating)

        iframe = folium.IFrame(html)
        popup = folium.Popup(iframe,
                            min_width=200,
                            max_width=120)

        Locations.add_child(folium.Marker(location=[row.Lat,row.Lon], popup = popup))
      m.add_child(Locations)
    if (markers!=True):
      m=folium.Map(tiles='CartoDB positron', control=False, location = [df.Lat.mean(),df.Lon.mean()], zoom_start=zoom).add_to(f)
    if (HexHeat == 'Heat'):
      points=df[['Lat','Lon']].values.tolist()
      HeatMap(points, name="Heatmap").add_to(m)

    if (HexHeat == 'Hex'):
      hexed = Hexify(df, resolution = res)
      df_aggreg=hexed.groupby(['hex_id']).size().reset_index(name='counts')
      if (fillGeom==False):
        choropleth_map(df_aggreg, 'counts', zoom=zoom, initial_map=m)
      if (fillGeom!=False):
        if fillGeom==True:
          fillGeom='39049'
        if len(fillGeom)==5:
          fillpoly=poly_geojson(usa.geometry[usa.GEOID==fillGeom])
        elif len(fillGeom)==2:
          fillpoly=poly_geojson(usa.geometry[usa.STATEFP==fillGeom].unary_union)
        fillhexes=h3.polyfill_geojson(fillpoly,res)
        h3_df = pd.DataFrame([],columns=['h3_id','h3_geo_boundary'])
        for h3_hex in fillhexes:
          h3_geo_boundary = shapely.geometry.Polygon(
              h3.h3_to_geo_boundary(h3_hex,geo_json=True)
          )
          h3_df.loc[len(h3_df)]=[
                        h3_hex,
                        h3_geo_boundary
                    ]
        geoms = [shape(i) for i in h3_df.h3_geo_boundary]
        fillgpd = gpd.GeoDataFrame({'hex_id':h3_df.h3_id,'geometry':geoms})
        fillgpd.crs='EPSG:4269'

        folium.Choropleth(
            geo_data=fillgpd,
            name="choropleth",
            data=df_aggreg,
            columns=["hex_id", "counts"],
            key_on="feature.properties.hex_id",
            fill_color="Blues",
            fill_opacity=0.7,
            line_opacity=0.02,
            legend_name="Restaurant Counts",
            nan_fill_opacity = .05
        ).add_to(m)


    folium.LayerControl().add_to(m)

    st.session_state.map = st_folium(m, width=700, height=450)
  
  return(st.session_state.map)

def show_map(df, markers = True, HexHeat = 'Hex', res = 8, zoom = 9, fillGeom=False):
    m = MapYelps_allinone(df, markers, HexHeat, res, zoom, fillGeom)  # Get or create the map
    folium_static(m)

st.set_page_config(page_title="Mapping Demo", page_icon="🌍")
st.markdown("# Mapping Demo")
st.sidebar.header("Mapping Demo")
st.write(
    """This demo shows how to use
[`st.pydeck_chart`](https://docs.streamlit.io/library/api-reference/charts/st.pydeck_chart)
to display geospatial data. It should now show an updated YELP map"""
)

Geog = st.text_input("Search Geography", "Columbus, Ohio")
Query = st.text_input("Search Query", "barbecue")

test = get_businesses(Geog, Query, st.secrets["YelpAPIKey"])
st.write(test)

# MapYelps(test)
show_map(test, markers = False, HexHeat = 'Hex', fillGeom=True, res = 7, zoom = 9)
st.write('test complete')

