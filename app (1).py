from pathlib import Path
import json,re,unicodedata,urllib.request
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from rapidfuzz import process, fuzz
st.set_page_config(page_title='EcoIntel Punjab',layout='wide',page_icon='🌿')
ROOT=Path(__file__).resolve().parent
@st.cache_data
def load():
 return (pd.read_csv(ROOT/'observations.csv',parse_dates=['date']),pd.read_csv(ROOT/'facilities.csv'),pd.read_csv(ROOT/'factors.csv',parse_dates=['date']))
D,F,A=load()
MET={'aqi':'AQI','pm25':'PM2.5 (µg/m³)','pm10':'PM10 (µg/m³)','no2':'NO₂ (µg/m³)','so2':'SO₂ (µg/m³)','co':'CO (mg/m³)'}
COL=['#218c74','#e5bd42','#f39b45','#dc5656','#8855a5','#791f38']; BANDS=['0–50','51–100','101–150','151–200','201–300','301–500']
def band(x): return pd.cut(x,[-1,50,100,150,200,300,float('inf')],labels=BANDS)
def norm(x):
 x=unicodedata.normalize('NFKD',str(x));x=''.join(c for c in x if not unicodedata.combining(c));x=re.sub(r'\bdistrict\b','',x.lower());x=re.sub('[^a-z0-9]','',x)
 return {'dgkhan':'deraghazikhan','deragazikhan':'deraghazikhan','shekhupura':'sheikhupura','sheikhu pura':'sheikhupura','rahimyarkhan':'rahimyarkhan','rahimyarkhandistrict':'rahimyarkhan','rahimyarkhan':'rahimyarkhan','leiah':'layyah','mandibahuddin':'mandibahauddin','pakpatan':'pakpattan','chinyot':'chiniot','nankana':'nankanasahib','dera gazi khan':'deraghazikhan','rahimyar khan':'rahimyarkhan'}.get(x,x)
@st.cache_data(ttl=86400,show_spinner=False)
def geo():
 local=ROOT/'pakistan_adm2.geojson'
 if local.exists():return json.loads(local.read_text())
 with urllib.request.urlopen('https://www.geoboundaries.org/api/current/gbOpen/PAK/ADM2/',timeout=30) as r: meta=json.load(r)
 with urllib.request.urlopen(meta['simplifiedGeometryGeoJSON'],timeout=60) as r:return json.load(r)
def plot(fig):
 fig.update_layout(template='plotly_white',margin=dict(l=8,r=8,t=20,b=8));st.plotly_chart(fig,use_container_width=True)
def table(df):st.dataframe(df,hide_index=True,use_container_width=True)
st.markdown('<style>[data-testid="stSidebar"]{background:#e6f0eb}[data-testid="stMetric"]{border:1px solid #dce7e2;padding:12px;border-radius:10px}h1,h2,h3{color:#14594b}</style>',unsafe_allow_html=True)
st.title('EcoIntel Punjab | Environmental Intelligence')
st.caption('RESEARCH PROTOTYPE • All readings, facility records and site coordinates are synthetic. No official affiliation.')
city=st.sidebar.selectbox('City / district',['All Punjab']+sorted(D.city.unique())); day=st.sidebar.date_input('Observation date',D.date.max().date(),min_value=D.date.min().date(),max_value=D.date.max().date()); metric=st.sidebar.selectbox('Map indicator',list(MET),format_func=MET.get)
S=D[D.date.eq(pd.Timestamp(day))]; upper=500 if metric=='aqi' else float(D[metric].max()); fig=go.Figure()
def points(df,label='Monitoring sites'):
 fig.add_trace(go.Scattermap(lat=df.latitude,lon=df.longitude,mode='markers+text',text=[f'{n}<br>{v:.0f}' for n,v in zip(df.location_name,df[metric])],textposition='top center',marker=dict(size=15,color=df[metric],colorscale='Turbo',cmin=0,cmax=upper,showscale=True,colorbar=dict(title=MET[metric])),customdata=df[['location_name','aqi','pm25','pm10','no2','so2','co']],hovertemplate='%{customdata[0]}<br>AQI %{customdata[1]}<br>PM2.5 %{customdata[2]}<br>PM10 %{customdata[3]}<br>NO₂ %{customdata[4]}<br>SO₂ %{customdata[5]}<br>CO %{customdata[6]}<extra></extra>',name=label))
if city=='All Punjab':
 st.subheader('Punjab • district air quality atlas'); M=S.groupby('city',as_index=False)[list(MET)+['latitude','longitude']].mean(); keys={norm(c):c for c in M.city}; used=set(); features=[]; records=[]
 try:
  for i,feature in enumerate(geo()['features']):
   raw=feature['properties'].get('shapeName',''); k=norm(raw); match=k if k in keys else None
   if not match:
    hit=process.extractOne(k,list(keys),scorer=fuzz.ratio)
    if hit and hit[1]>=88:match=hit[0]
   if not match or match in used:continue
   used.add(match); name=keys[match]; features.append({**feature,'id':name}); records.append(M[M.city.eq(name)].iloc[0].to_dict())
  if not records:raise ValueError('No district matches')
  T=pd.DataFrame(records); gj={'type':'FeatureCollection','features':features}
  if metric=='aqi':
   for b,c in zip(BANDS,COL):
    t=T[band(T.aqi)==b];
    if len(t):fig.add_trace(go.Choroplethmap(geojson=gj,locations=t.city,z=[1]*len(t),colorscale=[[0,c],[1,c]],zmin=0,zmax=1,showscale=False,showlegend=True,name=b,marker=dict(opacity=.85,line=dict(color='white',width=1)),customdata=t[['city','aqi','pm25']],hovertemplate='%{customdata[0]}<br>AQI %{customdata[1]:.0f}<br>PM2.5 %{customdata[2]:.1f}<extra></extra>'))
  else:fig.add_trace(go.Choroplethmap(geojson=gj,locations=T.city,z=T[metric],colorscale='YlOrRd',zmin=0,zmax=upper,marker=dict(opacity=.85,line=dict(color='white',width=1)),colorbar=dict(title=MET[metric])))
  fig.add_trace(go.Scattermap(lat=T.latitude,lon=T.longitude,mode='text',text=[f'{n}<br>{v:.0f}' for n,v in zip(T.city,T[metric])],hoverinfo='skip',showlegend=False,textfont=dict(size=10,color='#142c25')))
  missing=M[~M.city.isin(T.city)]
  if len(missing):
   fig.add_trace(go.Scattermap(lat=missing.latitude,lon=missing.longitude,mode='markers+text',text=[f'{n}: {v:.0f}' for n,v in zip(missing.city,missing[metric])],marker=dict(size=10,color='#64748b'),name='Boundary unavailable'))
   st.caption('Unmatched boundary areas (shown as points): '+', '.join(missing.city))
 except Exception as e:
  st.warning('Boundary service unavailable; showing city points. '+str(e)); points(M.rename(columns={'city':'location_name'}),'City averages')
 fig.update_layout(map=dict(style='carto-positron',center=dict(lat=31.1,lon=72.5),zoom=5.6),height=780,legend=dict(orientation='h',y=-.02));plot(fig)
 st.caption('Boundaries: geoBoundaries Pakistan ADM2. Historical boundary vintage may omit newer districts. Fill values are synthetic site averages; AQI bands illustrative.')
else:
 s=S[S.city.eq(city)].copy(); f=F[F.city.eq(city)]; h=D[D.city.eq(city)&D.date.le(pd.Timestamp(day))]; a=A[A.city.eq(city)&A.date.eq(pd.Timestamp(day))].iloc[0]
 st.subheader(f'{city} • local environmental intelligence')
 for col,(label,value) in zip(st.columns(4),[('Mean AQI',f'{s.aqi.mean():.0f}'),('PM2.5',f'{s.pm25.mean():.1f} µg/m³'),('Demo monitoring sites',len(s)),('Demo facilities',len(f))]):col.metric(label,value)
 points(s); layers=st.multiselect('Facility overlays',['Brick kiln','Factory'])
 for layer in layers:
  x=f[f.sector.eq(layer)];fig.add_trace(go.Scattermap(lat=x.latitude,lon=x.longitude,mode='markers',marker=dict(size=11,color='#a16207' if layer=='Brick kiln' else '#2563eb'),text=x.facility_name,customdata=x.compliance,hovertemplate='%{text}<br>%{customdata}<extra></extra>',name=layer))
 fig.update_layout(map=dict(style='carto-positron',center=dict(lat=s.latitude.mean(),lon=s.longitude.mean()),zoom=10.5),height=560);plot(fig)
 st.caption('Named areas are illustrative; marker coordinates are not verified monitoring or facility positions.')
 st.subheader('Local monitoring locations');table(s[['location_name','site_type']+list(MET)].rename(columns=MET).sort_values('AQI',ascending=False))
 t1,t2,t3=st.tabs(['Pollution factors','Factories & brick kilns','Historical trends'])
 with t1:
  table(pd.DataFrame({'Factor':['Wind speed (m/s)','Mixing height (m)','Humidity (%)','Traffic index (0–100)','Demo fire detections'],'Value':[round(a.wind_ms,2),round(a.mixing_m,1),a.humidity_pct,a.traffic_index,a.fire_detections_demo]}));st.caption('Simulated indicators, not source apportionment or causal estimates.');plot(px.scatter(h,x='wind_ms',y='pm25',color='location_name'))
 with t2:
  st.caption('Fictional facility registry snapshot: 23 November 2026; independent of selected map date.')
  for col,(label,val) in zip(st.columns(3),[('Brick kilns',sum(f.sector.eq('Brick kiln'))),('Factories',sum(f.sector.eq('Factory'))),('Demo fines',f'PKR {f.fine_pkr.sum():,}')]):col.metric(label,val)
  table(f[['facility_name','sector','technology_or_industry','compliance','fine_pkr']]);st.download_button('Download facility register',f.to_csv(index=False),'facilities.csv')
 with t3:plot(px.line(h.sort_values('date'),x='date',y=metric,color='location_name',labels=MET))
 st.download_button('Download selected city readings',s.to_csv(index=False),'city_readings.csv')
st.caption('EcoIntel Punjab | Synthetic demonstration • Not for regulatory decisions')
