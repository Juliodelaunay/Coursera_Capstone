#!/usr/bin/env python
# coding: utf-8

# ## Agrupacion y Segmentacion de Vecindarios de Toronto 

# #### Parte 1

# In[114]:


# Importacion de Librerias necesarias


# In[115]:


pip install BeautifulSoup4


# In[116]:


pip install lxml


# In[117]:


from bs4 import BeautifulSoup  
import requests 
import pandas as pd
import lxml


# In[118]:


#Importacion , Scraping y Creacion de Dataframe


# In[119]:


url =requests.get ("https://en.wikipedia.org/w/index.php?title=List_of_postal_codes_of_Canada:_M&oldid=958430791").text


# In[120]:


soup = BeautifulSoup(url,'lxml')


# In[121]:


My_table = soup.find('table',{'class':'wikitable sortable'})
df = pd.read_html(str(My_table))[0]
df.head()


# In[122]:


# Eliminamos Municipios 'Not assigned'


# In[123]:


drop_Not=df[df['Borough']=='Not assigned'].index
df.drop (drop_Not, inplace=True)
df.reset_index(drop=True, inplace=True)


# In[124]:


df.head()


# In[125]:


# Asignamos Vecindarios 'Not assigned' a Municipio


# In[193]:


df[df['Neighborhood']=='Not assigned']=df['Borough'].reset_index()
df.head()


# In[194]:


# Requerimiento filas-columnas


# In[195]:


df.shape


# #### Parte 2

# In[196]:


# Importacion de archivo csv con coordenadas


# In[197]:



from io import StringIO

url = requests.get(' http://cocl.us/Geospatial_data')
csv_raw = StringIO(url.text)
datos_geo = pd.read_csv(csv_raw)


# In[198]:


datos_geo.head()


# In[199]:


# Relacionamos Dataframes 


# In[200]:


df=pd.merge(df,datos_geo,how='left')


# In[201]:


df.head()


# #### Parte 3

# In[202]:


# Importacion Librerias Necesarias


# In[203]:


import numpy as np
import json
get_ipython().system('conda install -c conda-forge geopy --yes ')
from geopy.geocoders import Nominatim
from pandas.io.json import json_normalize 
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
from sklearn.cluster import KMeans
import folium
print('Librerias importadas')


# In[204]:


# Filtramos a Municipios que sean ' Toronto '


Tor_d = df[df['Borough'].str.contains('Toronto')].reset_index(drop=True)
Tor_d.head()


# In[205]:


# Obtenemos nro filas 

Tor_d.shape


# In[206]:


# Obtenemos coordenadas para Toronto

address = 'Toronto, ON'

geolocator = Nominatim(user_agent="ny_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude
print('Coordenadas Toronto {}, {}.'.format(latitude, longitude))


# In[207]:


# Creamos mapa de Toronto y añadimos los marcadores

map_Toronto = folium.Map(location=[latitude, longitude], zoom_start=10)

for lat, lng, borough, neighborhood in zip(Tor_d['Latitude'], Tor_d['Longitude'], Tor_d['Borough'], Tor_d['Neighborhood']):
    label = '{}, {}'.format(neighborhood, borough)
    label = folium.Popup(label, parse_html=True)
    folium.CircleMarker(
        [lat, lng],
        radius=5,
        popup=label,
        color='blue',
        fill=True,
        fill_color='#3186cc',
        fill_opacity=2,
        parse_html=False).add_to(map_Toronto)  
    
map_Toronto


# In[245]:


# Definimos version y credenciales para la API de Foursquare con un limite de 50 devoluciones

CLIENT_ID = 'DBBPKNBZNEC2JFO4JL13AJOJLMHLHOCOYWGTY5ZXJFXRJXYD' 
CLIENT_SECRET = 'YA51Q1Y4XHBRUZE1025SHVN3AKMX20MJHBBELS0BANSJWKMA' 
VERSION = '20180605' 
LIMIT = 50 


# In[246]:


# Definimos funcion para obtener los 100 sitios en un radio de 500 mts para cada barrio

def getNearbyVenues(names, latitudes, longitudes, radius=500):
    
    venues_list=[]
    for name, lat, lng in zip(names, latitudes, longitudes):
        print(name)
            
        # crear la URL de solicitud de API
        url = 'https://api.foursquare.com/v2/venues/explore?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'.format(
            CLIENT_ID, 
            CLIENT_SECRET, 
            VERSION, 
            lat, 
            lng, 
            radius, 
            LIMIT)
                # solicitud GET
        results = requests.get(url).json()["response"]['groups'][0]['items']
        
        # regresa solo información relevante de cada sitio cercano
        venues_list.append([(
            name, 
            lat, 
            lng, 
            v['venue']['name'], 
            v['venue']['location']['lat'], 
            v['venue']['location']['lng'],  
            v['venue']['categories'][0]['name']) for v in results])

    nearby_venues = pd.DataFrame([item for venue_list in venues_list for item in venue_list])
    nearby_venues.columns = ['Neighborhood', 
                  'Neighborhood Latitude', 
                  'Neighborhood Longitude', 
                  'Venue', 
                  'Venue Latitude', 
                  'Venue Longitude', 
                  'Venue Category']
    
    return(nearby_venues)


# In[247]:


# Corremos la funcion getNearbyVenues para cada barrio creando un Dataframe 'Toronto_venues'

Toronto_venues = getNearbyVenues(names=Tor_d['Neighborhood'],
                                   latitudes=Tor_d['Latitude'],
                                   longitudes=Tor_d['Longitude'])
                                  


# In[248]:


# mostramos Dataframe y revisamos tamaño

print(Toronto_venues.shape)
Toronto_venues.head()


# In[249]:


# Observemos cuantos sitios se devolvieron por barrio

Toronto_venues.groupby('Neighborhood').count()


# In[250]:


# Vemos cuantas categorias unicas hay por barrio

print('There are {} uniques categories.'.format(len(Toronto_venues['Venue Category'].unique())))


# In[251]:


#Analizamos cada barrio



# codificación
Toronto_onehot = pd.get_dummies(Toronto_venues[['Venue Category']], prefix="", prefix_sep="")

# añadir la columna de barrio de regreso al dataframe
Toronto_onehot['Neighborhood'] = Toronto_venues['Neighborhood'] 

# mover la columna de barrio a la primer columna
fixed_columns = [Toronto_onehot.columns[-1]] + list(Toronto_onehot.columns[:-1])
Toronto_onehot = Toronto_onehot[fixed_columns]

Toronto_onehot.shape


# In[252]:


# Agrupamos las filas por barrios tomando el parametro de promedio de ocurrencia de cada categoria


Toronto_grouped = Toronto_onehot.groupby('Neighborhood').mean().reset_index()
Toronto_grouped


# In[254]:


#Observamos tamaño Dataframe

Toronto_grouped.shape


# In[255]:


# Visualizamos cada barrio con los 12 lugares mas comunes

num_top_venues = 12

for hood in Toronto_grouped['Neighborhood']:
    print("----"+hood+"----")
    temp = Toronto_grouped[Toronto_grouped['Neighborhood'] == hood].T.reset_index()
    temp.columns = ['venue','freq']
    temp = temp.iloc[1:]
    temp['freq'] = temp['freq'].astype(float)
    temp = temp.round({'freq': 2})
    print(temp.sort_values('freq', ascending=False).reset_index(drop=True).head(num_top_venues))
    print('\n')


# In[256]:


# Creamos una funcion para ordenar en forma descendente los lugares

def return_most_common_venues(row, num_top_venues):
    row_categories = row.iloc[1:]
    row_categories_sorted = row_categories.sort_values(ascending=False)
    
    return row_categories_sorted.index.values[0:num_top_venues]


# In[257]:


# mostramos los primeros 12 lugares de cada barrio en un Dataframe nuevo

num_top_venues = 12

indicators = ['st', 'nd', 'rd']

# crear las columnas acorde al numero de sitios populares
columns = ['Neighborhood']
for ind in np.arange(num_top_venues):
    try:
        columns.append('{}{} Most Common Venue'.format(ind+1, indicators[ind]))
    except:
        columns.append('{}th Most Common Venue'.format(ind+1))

# crear un nuevo dataframe
neighborhoods_venues_sorted = pd.DataFrame(columns=columns)
neighborhoods_venues_sorted['Neighborhood'] = Toronto_grouped['Neighborhood']

for ind in np.arange(Toronto_grouped.shape[0]):
    neighborhoods_venues_sorted.iloc[ind, 1:] = return_most_common_venues(Toronto_grouped.iloc[ind, :], num_top_venues)

neighborhoods_venues_sorted.head()


# In[259]:


# establecer el número de agrupaciones en 5
kclusters = 5

Toronto_grouped_clustering = Toronto_grouped.drop('Neighborhood', 1)

# ejecutar k-means
kmeans = KMeans(n_clusters=kclusters, random_state=0).fit(Toronto_grouped_clustering)

# revisar las etiquetas de las agrupaciones generadas para cada fila del dataframe
kmeans.labels_[0:5] 


# In[260]:


# añadir etiquetas
neighborhoods_venues_sorted.insert(0, 'Cluster Labels', kmeans.labels_)

Toronto_merged = Tor_d

# juntar Toronto_grouped con Toronto_data 
Toronto_merged = Toronto_merged.join(neighborhoods_venues_sorted.set_index('Neighborhood'), on='Neighborhood')
Toronto_merged['Cluster Labels'] = Toronto_merged['Cluster Labels'].fillna("0").astype(int)


Toronto_merged.head() # revisar las ultimas columnas


# In[261]:


# creamos mapa de agrupacion
map_clusters = folium.Map(location=[latitude, longitude], zoom_start=11)

# establecer el esquema de color para las agrupaciones
x = np.arange(kclusters)
ys = [i + x + (i*x)**2 for i in range(kclusters)]
colors_array = cm.rainbow(np.linspace(0, 1, len(ys)))
rainbow = [colors.rgb2hex(i) for i in colors_array]

# añadir marcadores al mapa
markers_colors = []
for lat, lon, poi, cluster in zip(Toronto_merged['Latitude'], Toronto_merged['Longitude'], Toronto_merged['Neighborhood'], Toronto_merged['Cluster Labels']):
    label = folium.Popup(str(poi) + ' Cluster ' + str(cluster), parse_html=True)
    folium.CircleMarker(
        [lat, lon],
        radius=5,
        popup=label,
        color=rainbow[cluster-1],
        fill=True,
        fill_color=rainbow[cluster-1],
        fill_opacity=0.7).add_to(map_clusters)
       
map_clusters


# In[262]:


# Examinamos las agrupaciones pudiendo observar que categorias distinguen a cada agrupacion


# In[263]:


Toronto_merged.loc[Toronto_merged['Cluster Labels'] == 0, Toronto_merged.columns[[2] + list(range(5, Toronto_merged.shape[1]))]]


# In[264]:


Toronto_merged.loc[Toronto_merged['Cluster Labels'] == 1, Toronto_merged.columns[[2] + list(range(5, Toronto_merged.shape[1]))]]


# In[265]:


Toronto_merged.loc[Toronto_merged['Cluster Labels'] == 2, Toronto_merged.columns[[2] + list(range(5, Toronto_merged.shape[1]))]]


# In[266]:


Toronto_merged.loc[Toronto_merged['Cluster Labels'] == 3, Toronto_merged.columns[[2] + list(range(5, Toronto_merged.shape[1]))]]


# In[267]:


Toronto_merged.loc[Toronto_merged['Cluster Labels'] == 4, Toronto_merged.columns[[2] + list(range(5, Toronto_merged.shape[1]))]]


# 
