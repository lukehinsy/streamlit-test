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

import pandas as pd
import pydeck as pdk
# import geopandas as gpd
import pandas as pd
from census import Census
from us import states
import os
import plotly.express as px
import json
import pygris

import streamlit as st
from streamlit.hello.utils import show_code


def mapping_demo():

    c = Census(st.secrets['CensusAPIKey'])
    stAbbrevs=[]
    for x in states.STATES:
        stAbbrevs.append(x.abbr)
    
    df = pd.DataFrame(columns=('NAME',	'C17002_001E',	'C17002_002E',	'C17002_003E',	'B01003_001E','B25077_001E', 'B25097_001E',	'state',	'county'))
    for x in states.STATES:
        results = c.acs5.state_county(fields = ('NAME', 'C17002_001E', 'C17002_002E', 'C17002_003E', 'B01003_001E','B25077_001E', 'B25097_001E'),
                                      state_fips = x.fips,
                                      county_fips = "*",
                                      year = 2020)
        df=pd.concat([df, pd.DataFrame(results)])
    df.rename(columns = {'B25077_001E': 'MedianHHValue','B01003_001E':'TotalPop'}, inplace=True)
    df['poverty_rate'] = (df.C17002_002E + df.C17002_003E) / df.B01003_001E
    df.drop(['C17002_001E','C17002_002E','C17002_003E'], axis=1, inplace=True)


    pygris.counties(state = StateAbb , cb = True, cache = True)

    geom_df=pd.DataFrame(columns=('GEOID','NAME','NAMELSAD','STUSPS','geometry'))

    for x in states.STATES:
        tractmaps = pygris.counties(state = x.fips, cb = True, cache = True)
        geom_df=pd.concat([geom_df, tractmaps[['GEOID','NAME','NAMELSAD','STUSPS','geometry']]])

    geom_json = json.loads(geom_df.rename(columns={"GEOID": "fips"}).to_json())
    df['fips']=df.state+df.county
    fig = px.choropleth(df[['fips','NAME','MedianHHValue']], geojson=geom_json, locations='fips', color='MedianHHValue',
                           color_continuous_scale="Viridis",
                           range_color=(0, 400000),
                           scope="usa",
                           featureidkey = 'properties.fips',
                           hover_data = ['NAME','MedianHHValue'],
                           labels={'NAME':'County','MedianHHValue':'median HH value'}
                          )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.update_traces(marker_line_width=0, marker_line_color='rgba(0,0,0,0)')
    fig.show()

    # try:
    #     ALL_LAYERS = {
    #         "Bike Rentals": pdk.Layer(
    #             "HexagonLayer",
    #             data=from_data_file("bike_rental_stats.json"),
    #             get_position=["lon", "lat"],
    #             radius=200,
    #             elevation_scale=4,
    #             elevation_range=[0, 1000],
    #             extruded=True,
    #         ),
    #         "Bart Stop Exits": pdk.Layer(
    #             "ScatterplotLayer",
    #             data=from_data_file("bart_stop_stats.json"),
    #             get_position=["lon", "lat"],
    #             get_color=[200, 30, 0, 160],
    #             get_radius="[exits]",
    #             radius_scale=0.05,
    #         ),
    #         "Bart Stop Names": pdk.Layer(
    #             "TextLayer",
    #             data=from_data_file("bart_stop_stats.json"),
    #             get_position=["lon", "lat"],
    #             get_text="name",
    #             get_color=[0, 0, 0, 200],
    #             get_size=10,
    #             get_alignment_baseline="'bottom'",
    #         ),
    #         "Outbound Flow": pdk.Layer(
    #             "ArcLayer",
    #             data=from_data_file("bart_path_stats.json"),
    #             get_source_position=["lon", "lat"],
    #             get_target_position=["lon2", "lat2"],
    #             get_source_color=[200, 30, 0, 160],
    #             get_target_color=[200, 30, 0, 160],
    #             auto_highlight=True,
    #             width_scale=0.0001,
    #             get_width="outbound",
    #             width_min_pixels=3,
    #             width_max_pixels=30,
    #         ),
    #     }
    #     st.sidebar.markdown("### Map Layers")
    #     selected_layers = [
    #         layer
    #         for layer_name, layer in ALL_LAYERS.items()
    #         if st.sidebar.checkbox(layer_name, True)
    #     ]
    #     if selected_layers:
    #         st.pydeck_chart(
    #             pdk.Deck(
    #                 map_style=None,
    #                 initial_view_state={
    #                     "latitude": 37.76,
    #                     "longitude": -122.4,
    #                     "zoom": 11,
    #                     "pitch": 50,
    #                 },
    #                 layers=selected_layers,
    #             )
    #         )
    #     else:
    #         st.error("Please choose at least one layer above.")
    # except URLError as e:
    #     st.error(
    #         """
    #         **This demo requires internet access.**
    #         Connection error: %s
    #     """
    #         % e.reason
    #     )


st.set_page_config(page_title="Mapping Demo", page_icon="🌍")
st.markdown("# Mapping Demo")
st.sidebar.header("Mapping Demo")
st.write(
    """This demo shows how to use
[`st.pydeck_chart`](https://docs.streamlit.io/library/api-reference/charts/st.pydeck_chart)
to display geospatial data."""
)

mapping_demo()

show_code(mapping_demo)
