import folium
from html import escape
from math import radians, sin, cos, asin, sqrt

COL=['#218c74','#b59b18','#e08024','#dc5656','#8855a5','#791f38']
def color(aqi):
    return COL[sum(float(aqi)>v for v in [50,100,150,200,300])]
def distance(a,b,c,d):
    x,y,z,w=map(radians,[a,b,c,d]); return 6371*2*asin(min(1,sqrt(sin((z-x)/2)**2+cos(x)*cos(z)*sin((w-y)/2)**2)))
def detail(title, rows):
    return '<div style="font:14px Arial;min-width:250px"><h3>'+escape(str(title))+'</h3><small>SIMULATED DATA</small><table style="width:100%;line-height:1.6">'+''.join('<tr><td>'+escape(str(k))+'</td><td><b>'+escape(str(v))+'</b></td></tr>' for k,v in rows)+'</table></div>'
def make_map(s,f,metric,met):
    m=folium.Map(location=[s.latitude.mean(),s.longitude.mean()],zoom_start=11,tiles='CartoDB positron',control_scale=True)
    folium.TileLayer('OpenStreetMap',name='Street map').add_to(m)
    groups={k:folium.FeatureGroup(name=k,show=True).add_to(m) for k in ['Air quality stations','Factories','Brick kilns']}
    def icon(symbol,bg):
        return folium.DivIcon(html=f'<div style="background:{bg};color:white;border:2px solid white;border-radius:9px;box-shadow:0 2px 6px #5558;text-align:center;font:bold 14px Arial;width:42px;height:34px;line-height:30px">{symbol}</div>',icon_size=(42,34),icon_anchor=(21,17),popup_anchor=(0,-18))
    for r in s.itertuples():
        rows=[('Site type',r.site_type),('Observation date',str(r.date.date()))]+[(label,f'{getattr(r,k):.1f}') for k,label in met.items()]+[('Wind speed (m/s)',r.wind_ms),('Mixing height (m)',r.mixing_m),('Coordinates',f'{r.latitude:.5f}, {r.longitude:.5f}')]
        folium.Marker([r.latitude,r.longitude],icon=icon(f'{getattr(r,metric):.0f}' if metric=='aqi' else f'{getattr(r,metric):.1f}',color(r.aqi)),tooltip=f'{escape(r.location_name)} | AQI {r.aqi:.0f}',popup=folium.Popup(detail(r.location_name,rows),max_width=400)).add_to(groups['Air quality stations'])
    for r in f.itertuples():
        kiln=r.sector=='Brick kiln'; nearest=min(s.itertuples(),key=lambda n:distance(r.latitude,r.longitude,n.latitude,n.longitude)); km=distance(r.latitude,r.longitude,nearest.latitude,nearest.longitude)
        rows=[('Facility ID',r.facility_id),('Sector',r.sector),('Technology / industry',r.technology_or_industry),('Compliance',r.compliance),('Fine (PKR)',f'{r.fine_pkr:,.0f}'),('Registry date',r.snapshot_date),('Coordinates',f'{r.latitude:.5f}, {r.longitude:.5f}'),('Nearest demo station',nearest.location_name),('Distance (km)',f'{km:.2f}'),('Nearby station AQI',nearest.aqi),('Nearby station PM2.5 (µg/m³)',nearest.pm25),('Air observation date',str(nearest.date.date())),('Note','Nearby readings are not facility emissions or on-site measurements.')]
        folium.Marker([r.latitude,r.longitude],icon=icon('🔥' if kiln else '🏭','#b45309' if kiln else '#2563eb'),tooltip=f'{escape(r.facility_name)} | {escape(r.compliance)}',popup=folium.Popup(detail(r.facility_name,rows),max_width=430)).add_to(groups['Brick kilns' if kiln else 'Factories'])
    coords=s[['latitude','longitude']].values.tolist()+f[['latitude','longitude']].values.tolist()
    m.fit_bounds(coords,padding=(35,35),max_zoom=13)
    folium.LayerControl(collapsed=False).add_to(m)
    return m
