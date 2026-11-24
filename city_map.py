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
def hourly_chart(aqi, station, day):
    # Demonstration profile, not measured hourly data. Mean equals daily AQI.
    import random
    from statistics import mean
    rng=random.Random(f'{station}-{day}')
    weights=[1+0.22*cos((h-2)*3.141592653589793/12)+rng.uniform(-.08,.08) for h in range(24)]
    avg=mean(weights)
    values=[aqi*w/avg for w in weights]
    top=max(100, max(values)*1.12)
    x=lambda h: 42+h*310/23
    y=lambda v: 145-v/top*120
    path=' '.join(('M' if h==0 else 'L')+f'{x(h):.1f},{y(v):.1f}' for h,v in enumerate(values))
    grid=''.join(f'<line x1="42" y1="{y(v):.1f}" x2="352" y2="{y(v):.1f}" stroke="#ddd"/><text x="36" y="{y(v)+4:.1f}" text-anchor="end" font-size="10">{v:.0f}</text>' for v in [0,top/2,top])
    ticks=''.join(f'<text x="{x(h):.1f}" y="160" text-anchor="middle" font-size="10">{h:02d}:00</text>' for h in [0,6,12,18,23])
    dots=''.join(f'<circle cx="{x(h):.1f}" cy="{y(v):.1f}" r="3" fill="#14594b"><title>{h:02d}:00 — AQI {v:.1f}</title></circle>' for h,v in enumerate(values))
    return f'<div style="margin-top:12px;font:13px Arial"><b>Hourly AQI • {day}</b><br><small>Simulated hourly profile from daily AQI; PKT</small><svg viewBox="0 0 370 174" width="100%" xmlns="http://www.w3.org/2000/svg">{grid}<path d="{path}" fill="none" stroke="#14594b" stroke-width="2.5"/>{dots}{ticks}</svg><small>Min {min(values):.0f} · Max {max(values):.0f} · Mean {mean(values):.0f}</small></div>'

def make_map(s,f,metric,met):
    m=folium.Map(location=[s.latitude.mean(),s.longitude.mean()],zoom_start=11,tiles='CartoDB positron',control_scale=True)
    folium.TileLayer('OpenStreetMap',name='Street map').add_to(m)
    groups={k:folium.FeatureGroup(name=k,show=True).add_to(m) for k in ['Air quality stations','Factories','Brick kilns']}
    def icon(symbol,bg):
        return folium.DivIcon(html=f'<div style="background:{bg};color:white;border:2px solid white;border-radius:9px;box-shadow:0 2px 6px #5558;text-align:center;font:bold 14px Arial;width:42px;height:34px;line-height:30px">{symbol}</div>',icon_size=(42,34),icon_anchor=(21,17),popup_anchor=(0,-18))
    for r in s.itertuples():
        rows=[('Site type',r.site_type),('Observation date',str(r.date.date()))]+[(label,f'{getattr(r,k):.1f}') for k,label in met.items()]+[('Wind speed (m/s)',r.wind_ms),('Mixing height (m)',r.mixing_m),('Coordinates',f'{r.latitude:.5f}, {r.longitude:.5f}')]
        folium.Marker([r.latitude,r.longitude],icon=icon(f'{getattr(r,metric):.0f}' if metric=='aqi' else f'{getattr(r,metric):.1f}',color(r.aqi)),tooltip=f'{escape(r.location_name)} | AQI {r.aqi:.0f}',popup=folium.Popup(detail(r.location_name,rows)+hourly_chart(r.aqi,r.station_id,str(r.date.date())),max_width=440,min_width=370)).add_to(groups['Air quality stations'])
    for r in f.itertuples():
        kiln=r.sector=='Brick kiln'; nearest=min(s.itertuples(),key=lambda n:distance(r.latitude,r.longitude,n.latitude,n.longitude)); km=distance(r.latitude,r.longitude,nearest.latitude,nearest.longitude)
        rows=[('Facility ID',r.facility_id),('Sector',r.sector),('Technology / industry',r.technology_or_industry),('Compliance',r.compliance),('Fine (PKR)',f'{r.fine_pkr:,.0f}'),('Registry date',r.snapshot_date),('Coordinates',f'{r.latitude:.5f}, {r.longitude:.5f}'),('Nearest demo station',nearest.location_name),('Distance (km)',f'{km:.2f}'),('Nearby station AQI',nearest.aqi),('Nearby station PM2.5 (µg/m³)',nearest.pm25),('Air observation date',str(nearest.date.date())),('Note','Nearby readings are not facility emissions or on-site measurements.')]
        folium.Marker([r.latitude,r.longitude],icon=icon('🔥' if kiln else '🏭','#b45309' if kiln else '#2563eb'),tooltip=f'{escape(r.facility_name)} | {escape(r.compliance)}',popup=folium.Popup(detail(r.facility_name,rows),max_width=430)).add_to(groups['Brick kilns' if kiln else 'Factories'])
    coords=s[['latitude','longitude']].values.tolist()+f[['latitude','longitude']].values.tolist()
    m.fit_bounds(coords,padding=(35,35),max_zoom=13)
    folium.LayerControl(collapsed=False).add_to(m)
    return m
