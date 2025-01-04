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

import streamlit as st
from streamlit.hello.utils import show_code

def get_businesses(location, term, api_key):
    """
    Uses YelpAPI to pull up to 1000 businesses, Lat/Lon, Avg Rating, and   
    Number of Ratings (plus distance, but we aren't using that).  

    """
    headers = {'Authorization': 'Bearer %s' % api_key}
    url = 'https://api.yelp.com/v3/businesses/search'

    data = [] 
    for offset in range(0, 1000, 50):
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

MapYelps(test)

st.write('test complete')

