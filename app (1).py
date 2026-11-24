from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

st.set_page_config(page_title='EcoIntel Punjab',page_icon='🌿',layout='wide')
st.markdown('''<style>.block-container{padding-top:2rem} [data-testid="stMetric"]{border:1px solid #cbd9d1;border-radius:12px;padding:15px} </style>''',unsafe_allow_html=True)
@st.cache_data
def load():
    return pd.read_excel(Path(__file__).parent/'EPA_Punjab_Dashboard_Data.xlsx',sheet_name=None)
d=load(); a=d['Hourly_Synthetic']; w=d['Weather_Synthetic']; e=d['Enforcement_Synthetic']; g=d['District_Synthetic']
for t in (a,w): t['Timestamp']=pd.to_datetime(t.Timestamp)
for t in (e,g): t['Date']=pd.to_datetime(t.Date)
st.sidebar.title('EcoIntel Punjab')
page=st.sidebar.radio('Intelligence modules',['Executive overview','District intelligence','Pollution & weather','Predictive intelligence','Enforcement','Sensor quality','Policy simulation','Reported EPA figures','Export report'])
st.sidebar.caption('Prototype • 9–23 November 2026')
st.title('EcoIntel Punjab')
st.caption('Environmental intelligence & decision support | Independent consultation prototype')
st.warning('Synthetic demonstration data. AQI proxy is not an official EPA calculation. Reported figures are separately identified.')
period=st.sidebar.date_input('Analysis period',(a.Timestamp.min().date(),a.Timestamp.max().date()),min_value=a.Timestamp.min().date(),max_value=a.Timestamp.max().date())
if len(period)!=2: st.stop()
lo,hi=map(pd.Timestamp,period); hi+=pd.Timedelta(days=1)
stations=st.sidebar.multiselect('Monitoring stations',sorted(a.Station.unique()),default=sorted(a.Station.unique()))
x=a[a.Timestamp.between(lo,hi,inclusive='left') & a.Station.isin(stations)].copy(); y=w[w.Timestamp.between(lo,hi,inclusive='left')]; z=e[e.Date.between(lo,hi,inclusive='left')]; q=g[g.Date.between(lo,hi,inclusive='left')]
if x.empty: st.info('Select at least one station and a valid date range.'); st.stop()
city=x.groupby('Timestamp',as_index=False).mean(numeric_only=True).merge(y,on='Timestamp',how='left'); city['Hour']=city.Timestamp.dt.hour
poll=['AQI_proxy','PM2_5_ug_m3','PM10_ug_m3','NO2_ug_m3','SO2_ug_m3','CO_mg_m3']
def chart(fig): st.plotly_chart(fig,use_container_width=True)
def metrics():
    for c,(label,val) in zip(st.columns(4), [('Mean AQI proxy',f'{x.AQI_proxy.mean():.0f}'),('PM2.5 µg/m³',f'{x.PM2_5_ug_m3.mean():.1f}'),('Stations',x.Station.nunique()),('Hours proxy > 300',int((city.AQI_proxy>300).sum()))]): c.metric(label,val)
if page=='Executive overview':
    metrics(); chart(px.line(city,x='Timestamp',y='AQI_proxy',title='Hourly network mean AQI proxy'))
    l,r=st.columns(2)
    with l: chart(px.bar(x.groupby('Station',as_index=False).AQI_proxy.mean().sort_values('AQI_proxy'),x='AQI_proxy',y='Station',orientation='h',title='Station ranking'))
    with r: chart(px.bar(z.groupby('Sector',as_index=False).Inspections.sum(),x='Sector',y='Inspections',title='Inspection activity'))
    st.subheader('Decision brief'); st.write(f'Highest mean station proxy: {x.groupby("Station").AQI_proxy.mean().idxmax()}. Review persistent hotspots and weather conditions before assigning field resources.')
elif page=='District intelligence':
    st.caption('District data are separate synthetic series; station filters do not apply.')
    chart(px.bar(q.groupby('District',as_index=False).AQI_proxy.mean().sort_values('AQI_proxy'),x='AQI_proxy',y='District',orientation='h',title='District priority ranking'))
    chart(px.imshow(q.pivot_table(index='District',columns='Date',values='AQI_proxy'),aspect='auto',color_continuous_scale='YlOrRd',title='District-day risk matrix'))
    st.dataframe(q,use_container_width=True)
elif page=='Pollution & weather':
    p=st.selectbox('Pollutant',poll); v=st.selectbox('Weather variable',['Wind_m_s','Mixing_height_m','Ventilation_m2_s','Temperature_C','Rain_mm','Visibility_km'])
    chart(px.scatter(city,x=v,y=p,color='Hour',title='Weather association (not causation)'))
    chart(px.imshow(x.assign(Hour=x.Timestamp.dt.hour).pivot_table(index='Station',columns='Hour',values=p),aspect='auto',title='Diurnal station heatmap'))
    chart(px.bar_polar(y.assign(Direction=(y.Wind_from_deg/45).round()*45%360).groupby('Direction',as_index=False).Wind_m_s.count(),r='Wind_m_s',theta='Direction',title='Wind direction frequency'))
    chart(px.imshow(city[poll+[v]].corr(),zmin=-1,zmax=1,color_continuous_scale='RdBu_r',text_auto='.2f',title='Correlation matrix'))
elif page=='Predictive intelligence':
    st.caption('Short synthetic history: demonstration only. One-hour-ahead PM2.5 model with chronological holdout and persistence benchmark.')
    b=city.sort_values('Timestamp').copy(); target='PM2_5_ug_m3'; b['lag1']=b[target].shift(1); b['lag24']=b[target].shift(24); b['hour']=b.Timestamp.dt.hour; b['wind_lag']=b.Wind_m_s.shift(1); b['mix_lag']=b.Mixing_height_m.shift(1); features=['lag1','lag24','hour','wind_lag','mix_lag']; b=b.dropna(subset=features+[target]); n=int(len(b)*.75)
    if n<48 or len(b)-n<12: st.info('Select a longer date range.'); st.stop()
    model=RandomForestRegressor(n_estimators=120,min_samples_leaf=4,random_state=42,n_jobs=2).fit(b[features].iloc[:n],b[target].iloc[:n]); test=b.iloc[n:].copy(); test['Prediction']=model.predict(test[features]); test['Persistence']=test.lag1
    c1,c2=st.columns(2); c1.metric('Model MAE',f'{mean_absolute_error(test[target],test.Prediction):.1f}'); c2.metric('Persistence MAE',f'{mean_absolute_error(test[target],test.Persistence):.1f}')
    chart(px.line(test,x='Timestamp',y=[target,'Prediction','Persistence'],title='Held-out one-step predictions'))
    chart(px.bar(x=model.feature_importances_,y=features,orientation='h',title='Model feature importance (not causal)'))
    st.download_button('Download validation predictions',test.to_csv(index=False),'validation.csv')
elif page=='Enforcement':
    st.caption('District and sector totals; not facility-level violation records.')
    sector=st.multiselect('Sectors',sorted(z.Sector.unique()),default=sorted(z.Sector.unique())); z=z[z.Sector.isin(sector)]
    for c,k in zip(st.columns(4),['Inspections','Sealed','Fines_PKR','Hoods_fitted']): c.metric(k,f'{z[k].sum():,.0f}')
    chart(px.bar(z.groupby('Sector',as_index=False)[['Inspections','Sealed']].sum(),x='Sector',y=['Inspections','Sealed'],barmode='group'))
    chart(px.line(z.groupby('Date',as_index=False).Sealed.sum(),x='Date',y='Sealed',title='Daily sealing activity'))
    t=z.groupby('District',as_index=False)[['Inspections','Sealed','Fines_PKR']].sum(); t['Seals per 100 inspections']=100*t.Sealed/t.Inspections.replace(0,np.nan); st.dataframe(t,use_container_width=True)
elif page=='Sensor quality':
    s=st.selectbox('Station',stations); p=st.selectbox('Measure',poll); t=x[x.Station==s].sort_values('Timestamp').copy(); base=t[p].iloc[:max(2,len(t)//3)]; mu=base.mean(); sd=base.std(); t['EWMA']=t[p].ewm(alpha=.2,adjust=False).mean(); t['Flag']=(t[p]-mu).abs()>3*sd
    fig=px.line(t,x='Timestamp',y=[p,'EWMA']); fig.add_hline(y=mu+3*sd,line_dash='dash'); fig.add_hline(y=mu-3*sd,line_dash='dash'); chart(fig); st.caption('Exploratory baseline limits on raw observations; flags may reflect real pollution episodes, not sensor faults.'); st.dataframe(t[t.Flag][['Timestamp',p,'Flag']])
elif page=='Policy simulation':
    st.info('Hypothetical sensitivity analysis, not a calibrated causal or emissions model.')
    traffic=st.slider('Traffic emissions reduction (%)',0,100,20); industry=st.slider('Industrial emissions reduction (%)',0,100,30); burning=st.slider('Burning emissions reduction (%)',0,100,40); baseline=x.PM2_5_ug_m3.mean(); reduction=(.30*traffic+.25*industry+.20*burning)/100; scenario=baseline*(1-reduction)
    c1,c2,c3=st.columns(3); c1.metric('Baseline PM2.5',f'{baseline:.1f}'); c2.metric('Scenario PM2.5',f'{scenario:.1f}'); c3.metric('Assumed reduction',f'{reduction:.1%}'); chart(px.bar(x=['Baseline','Scenario'],y=[baseline,scenario],labels={'y':'PM2.5 µg/m³'})); st.caption('Assumed weights: traffic 30%, industry 25%, burning 20%; remaining 25% unchanged. Weights are illustrative.')
elif page=='Reported EPA figures':
    st.info('Extracted from the supplied EPA report, 1–15 November 2026. Independent of synthetic filters.'); r=d['Reported_Daily_AQI']; chart(px.bar(r,x='Date',y='AQI',title='Reported Lahore daily AQI')); chart(px.bar(d['Reported_Stations'],x='Station',y=['AQI_12_Nov','AQI_13_Nov'],barmode='group')); st.dataframe(d['Reported_Weather']); st.dataframe(d['Reported_Enforcement'])
else:
    metrics(); st.subheader('Download analytical brief'); brief=f'EcoIntel Punjab — SYNTHETIC DEMONSTRATION\nPeriod: {lo.date()} to {period[1]}\nMean AQI proxy: {x.AQI_proxy.mean():.1f}\nMean PM2.5: {x.PM2_5_ug_m3.mean():.1f} µg/m³\nStation count: {x.Station.nunique()}\nInspections (all selected dates): {z.Inspections.sum()}\nNot an official EPA report.'; st.text(brief); st.download_button('Download brief',brief,'environmental_brief.txt'); st.download_button('Download filtered observations',x.to_csv(index=False),'observations.csv')
