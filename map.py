from offline_folium import offline
import folium

m = folium.Map(
    location=[52.475024, 13.457575],
    zoom_start=19
)

m.save('assets/offline_map.html')