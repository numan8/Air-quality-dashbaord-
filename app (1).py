from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np
import json, re, urllib.request, unicodedata
import plotly.graph_objects as go
st.set_page_config(page_title='EcoIntel Punjab | Air Quality Atlas',page_icon='🌿',layout='wide')
ROOT=Path(__file__).parent
@st.cache_data
def load():
    d=pd.read_csv(ROOT/'observations.csv',parse_dates=['date']); return d
D=load()
COLORS=['#218c74','#e5bd42','#f39b45','#dc5656','#8855a5','#791f38']
BANDS=['0–50','51–100','101–150','151–200','201–300','301–500']
def band(x): return pd.cut(x,[-1,50,100,150,200,300,500],labels=BANDS)
def chart(fig):
    fig.update_layout(template='plotly_white',margin=dict(l=10,r=10,t=35,b=10),font=dict(family='Arial'),legend_title_text='');st.plotly_chart(fig,use_container_width=True)
st.markdown('''<style>.stApp{background:#f3f7f5}[data-testid="stMetric"]{background:white;border:1px solid #dbe7e1;border-radius:12px;padding:16px}[data-testid="stSidebar"]{background:#e6f0eb}h1,h2,h3{color:#14594b}</style>''',unsafe_allow_html=True)
st.title('EcoIntel Punjab | Air Quality Atlas')
st.caption('ENVIRONMENTAL INTELLIGENCE  /  PROVINCE-WIDE MONITORING  /  RESEARCH PROTOTYPE')
st.warning('Demonstration only • All measurements and monitoring locations are simulated. AQI bands are illustrative, not an official EPA classification.')
city=st.sidebar.selectbox('City / area',['All Punjab']+sorted(D.city.unique()))
day=st.sidebar.date_input('Map observation date',D.date.max().date(),min_value=D.date.min().date(),max_value=D.date.max().date())
metric=st.sidebar.selectbox('Map indicator',['aqi','pm25','pm10','no2','so2','co'],format_func=lambda x:{'aqi':'AQI','pm25':'PM2.5 (µg/m³)','pm10':'PM10 (µg/m³)','no2':'NO₂ (µg/m³)','so2':'SO₂ (µg/m³)','co':'CO (mg/m³)'}[x])
H=D if city=='All Punjab' else D[D.city==city]; S=H[H.date==pd.Timestamp(day)].copy(); S['band']=band(S.aqi)
C=D[D.date==pd.Timestamp(day)].groupby('city',as_index=False).agg(aqi=('aqi','mean'),pm25=('pm25','mean'),latitude=('latitude','mean'),longitude=('longitude','mean'))
cols=st.columns(4);cols[0].metric('Mean AQI',f'{S.aqi.mean():.0f}');cols[1].metric('Mean PM2.5',f'{S.pm25.mean():.1f} µg/m³');cols[2].metric('Simulated stations',len(S));cols[3].metric('Stations above AQI 300',int((S.aqi>300).sum()))
a,b,c,e,f=st.tabs(['Punjab AQI map','City trends','Weather intelligence','Risk & alerts','Data explorer'])
@st.cache_data(ttl=86400, show_spinner=False)
def boundaries():
    local=ROOT/'pakistan_adm2.geojson'
    if local.exists(): return json.loads(local.read_text(encoding='utf-8'))
    url='https://www.geoboundaries.org/api/current/gbOpen/PAK/ADM2/'
    with urllib.request.urlopen(url,timeout=30) as r: meta=json.load(r)
    with urllib.request.urlopen(meta['simplifiedGeometryGeoJSON'],timeout=60) as r: return json.load(r)
def normalize(x):
    x=unicodedata.normalize('NFKD',str(x)).lower()
    x=re.sub(r'\bdistrict\b','',x)
    x=re.sub(r'[^a-z0-9]','',x)
    return {'dgkhan':'deraghazikhan','deragazikhan':'deraghazikhan','rahimyarkhan':'rahimyarkhan','rahimyar khan':'rahimyarkhan','tobateksingh':'tobateksingh','mandibahauddin':'mandibahauddin','mandibahuddin':'mandibahauddin','sheikhupura':'sheikhupura','shekhupura':'sheikhupura','nankanasahib':'nankanasahib','pakpattan':'pakpattan','pakpat tan':'pakpattan','leiah':'layyah','layyah':'layyah','chinyot':'chiniot'}.get(x,x)
with a:
    st.subheader('Punjab district air quality • filled boundaries')
    level=st.radio('Map layer',['District boundaries','District boundaries + stations','Monitoring stations'],horizontal=True)
    M=D[D.date==pd.Timestamp(day)].groupby('city',as_index=False)[['aqi','pm25','pm10','no2','so2','co','latitude','longitude']].mean()
    M['key']=M.city.map(normalize); M['band']=band(M.aqi)
    center={'lat':31.1 if city=='All Punjab' else S.latitude.mean(),'lon':72.5 if city=='All Punjab' else S.longitude.mean()}
    fig=go.Figure(); matched=M.iloc[0:0]; ready=False
    if level!='Monitoring stations':
        try:
            geo=boundaries(); keys=set(M.key); features=[]
            for feature in geo['features']:
                key=normalize(feature['properties'].get('shapeName',''))
                if key in keys:
                    feature={**feature,'id':key}; features.append(feature)
            if not features: raise ValueError('No matching district names in boundary file')
            matched=M[M.key.isin({f['id'] for f in features})].copy(); ready=True
            gj={'type':'FeatureCollection','features':features}
            if metric=='aqi':
                for label,color in zip(BANDS,COLORS):
                    subset=matched[matched.band==label]
                    if subset.empty: continue
                    fig.add_trace(go.Choroplethmap(geojson=gj,locations=subset.key,z=[1]*len(subset),zmin=0,zmax=1,colorscale=[[0,color],[1,color]],showscale=False,showlegend=True,name=label,marker=dict(opacity=.78,line=dict(width=1.4,color='#ffffff')),customdata=subset[['city','aqi','pm25','pm10','no2','so2','co']].to_numpy(),hovertemplate='%{customdata[0]}<br>AQI: %{customdata[1]:.0f}<br>PM2.5: %{customdata[2]:.1f}<br>PM10: %{customdata[3]:.1f}<br>NO₂: %{customdata[4]:.1f}<br>SO₂: %{customdata[5]:.1f}<br>CO: %{customdata[6]:.2f}<extra></extra>'))
            else:
                fig.add_trace(go.Choroplethmap(geojson=gj,locations=matched.key,z=matched[metric],zmin=0,zmax=float(D[metric].max()),colorscale='YlOrRd',marker=dict(opacity=.8,line=dict(width=1.4,color='white')),customdata=matched[['city','aqi']].to_numpy(),hovertemplate='%{customdata[0]}<br>Value: %{z:.1f}<br>AQI: %{customdata[1]:.0f}<extra></extra>',colorbar=dict(title=metric)))
            fig.add_trace(go.Scattermap(lat=matched.latitude,lon=matched.longitude,mode='text',text=[f'{n}<br>{v:.0f}' for n,v in zip(matched.city,matched[metric])],textfont=dict(size=10,color='#152d29'),hoverinfo='skip',showlegend=False))
            missing=M[~M.key.isin(matched.key)]
            if not missing.empty: st.info('Boundary vintage/name mismatch: '+', '.join(missing.city)+'. These areas are shown as points, not invented polygons.')
            if not missing.empty: fig.add_trace(go.Scattermap(lat=missing.latitude,lon=missing.longitude,mode='markers',marker=dict(size=12,color=missing[metric],colorscale='YlOrRd',cmin=0,cmax=500 if metric=='aqi' else float(D[metric].max())),text=missing.city,customdata=missing[metric],hovertemplate='%{text}: %{customdata:.1f}<extra></extra>',name='Unmatched areas'))
        except Exception as exc:
            st.warning('District boundary data could not be loaded. Showing monitoring points instead. Add pakistan_adm2.geojson beside app.py for offline boundaries.')
            st.caption(str(exc))
    if level!='District boundaries' or not ready:
        fig.add_trace(go.Scattermap(lat=S.latitude,lon=S.longitude,mode='markers',marker=dict(size=9,color=S[metric],colorscale='YlOrRd',cmin=0,cmax=500 if metric=='aqi' else float(D[metric].max())),text=S.station_id,customdata=S[['city',metric]].to_numpy(),hovertemplate='%{customdata[0]} • %{text}<br>Value: %{customdata[1]:.1f}<extra></extra>',name='Simulated stations'))
    fig.update_layout(map=dict(style='carto-positron',center=center,zoom=5.6 if city=='All Punjab' else 8.5),height=720,legend=dict(orientation='h',y=-.02),margin=dict(l=0,r=0,t=0,b=0))
    chart(fig)
    st.caption('Boundary source: geoBoundaries gbOpen Pakistan ADM2 (boundary vintage may differ from current districts). Fill values are synthetic city-site means used as district proxies, not district-wide measured averages. AQI bands are illustrative.')
    st.subheader('Punjab city comparison • selected date');chart(px.bar(C.sort_values('aqi',ascending=False).head(15),x='city',y='aqi',color='aqi',color_continuous_scale='YlOrRd',range_color=[0,500]))
with b:
    st.subheader('Historical air quality'); end=pd.Timestamp(day); T=H[H.date<=end].groupby('date',as_index=False)[['aqi','pm25','pm10','no2','so2','co']].mean();T['7-day AQI']=T.aqi.rolling(7,min_periods=1).mean();chart(px.line(T,x='date',y=['aqi','7-day AQI'],labels={'value':'AQI'}));chart(px.line(T,x='date',y=metric));st.subheader('Station comparison');chart(px.bar(S.sort_values('aqi',ascending=False).head(25),x='station_id',y='aqi',color='site_type',hover_data=['city']))
with c:
    st.subheader('Meteorological associations'); chart(px.scatter(H,x='wind_ms',y='pm25',color='site_type',opacity=.45,labels={'wind_ms':'Wind speed (m/s)','pm25':'PM2.5 (µg/m³)'})); chart(px.scatter(H,x='mixing_m',y='pm25',color='site_type',opacity=.45)); st.caption('Simulated associations are not causal evidence.')
with e:
    st.subheader('Threshold-based screening'); threshold=st.slider('Illustrative AQI alert threshold',50,450,300,10); alerts=S[S.aqi>threshold].sort_values('aqi',ascending=False);st.metric('Stations flagged',len(alerts));st.dataframe(alerts[['city','station_id','site_type','aqi','pm25']],hide_index=True,use_container_width=True);chart(px.bar(C.sort_values('aqi',ascending=False),x='city',y='aqi',color='aqi',range_color=[0,500],color_continuous_scale='YlOrRd'))
with f:
    st.subheader('Filtered observations');st.dataframe(H,hide_index=True,use_container_width=True);st.download_button('Download filtered CSV',H.to_csv(index=False),'filtered_observations.csv','text/csv');st.download_button('Download full Excel workbook',(ROOT/'Punjab_Atlas_Data.xlsx').read_bytes(),'Punjab_Atlas_Data.xlsx')
st.caption('EcoIntel Punjab • Independent prototype • No official affiliation implied')
