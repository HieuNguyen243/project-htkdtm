import argparse, getpass, json, os, uuid
from urllib.parse import quote
from pathlib import Path
import requests

BASE=Path(__file__).parent
DB='PhongTro BI Demo'
ORIGIN='synthetic'
COUNT='COUNT(DISTINCT listing_id)'
MED='PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_vnd_month)'

def metric(sql,label):
    return dict(expressionType='SQL',sqlExpression=sql,label=label,optionName='metric_'+uuid.uuid5(uuid.NAMESPACE_URL,sql+label).hex,hasCustomLabel=True)
def filt(col,val,op='IN'):
    return dict(clause='WHERE',expressionType='SIMPLE',subject=col,operator=op,comparator=val)
def spec(name,ds,typ,metrics=(),x=None,cols=(),extra=(),fmt=',.0f'):
    return dict(name=name,ds=ds,typ=typ,metrics=[metric(s,l) for s,l in metrics],x=x,cols=list(cols),extra=list(extra),fmt=fmt)
def k(name,ds,sql,fmt=',.0f'): return spec(name,ds,'big_number_total',[(sql,name.split(' – ',1)[-1])],fmt=fmt)
def rate(n): return f'1.0 * SUM(affordable_{n}m) / NULLIF(SUM(valid_price),0)'
P='vw_market_price'; A='vw_affordability'; Q='vw_listing_quality'; B='vw_import_batch_quality'
D1=[k('D1.01 – Tổng tin đăng',P,COUNT),k('D1.02 – Giá hợp lệ',P,'SUM(valid_price)'),k('D1.03 – Giá trung vị',P,MED),k('D1.04 – P25',P,'PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY rent_vnd_month)'),k('D1.05 – P75',P,'PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY rent_vnd_month)'),k('D1.06 – Giá/m² trung vị',P,'PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_m2)'),spec('D1.07 – Giá theo quận',P,'echarts_timeseries_bar',[(MED,'Giá trung vị'),('SUM(valid_price)','Số mẫu')],x='district',extra=[filt('valid_price',[1])]),spec('D1.08 – Phân bố giá',P,'echarts_timeseries_bar',[(COUNT,'Số tin')],x='price_range',extra=[filt('valid_price',[1])]),spec('D1.09 – Giá/m² theo quận',P,'echarts_timeseries_bar',[('PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rent_per_m2)','Giá/m² trung vị')],x='district'),spec('D1.10 – Danh sách phòng',P,'table',cols=['listing_id','district','room_type','rent_vnd_month','area_m2','rent_per_m2','source_name'])]
# Keep unlike units off the same axis; sample counts are available in the table.
D1[6]['metrics']=D1[6]['metrics'][:1]
D2=[k('D2.01 – Tổng tin đăng',A,COUNT),k('D2.02 – Giá hợp lệ',A,'SUM(valid_price)'),k('D2.03 – Phù hợp 3 triệu',A,'SUM(affordable_3m)'),k('D2.04 – Tỷ lệ phù hợp',A,rate(3),'.2%'),k('D2.05 – Độ phủ giá',A,'1.0 * SUM(valid_price)/NULLIF(COUNT(*),0)','.2%'),k('D2.06 – Thiếu giá',A,'COUNT(*) FILTER (WHERE rent_vnd_month IS NULL)'),spec('D2.07 – So sánh ngân sách',A,'echarts_timeseries_bar',[(rate(n),f'{n} triệu') for n in [2,3,4,5]],x='price_basis',fmt='.0%'),spec('D2.08 – Phù hợp ngân sách 3 triệu',A,'pie',[(COUNT,'Số tin')],x='affordable_3m',extra=[filt('valid_price',[1])]),spec('D2.09 – Khả năng chi trả theo quận',A,'echarts_timeseries_bar',[(rate(3),'Tỷ lệ phù hợp')],x='district',fmt='.0%'),spec('D2.10 – Phòng phù hợp',A,'table',cols=['listing_id','district','room_type','rent_vnd_month','area_m2','deposit_vnd'],extra=[filt('affordable_3m',[1])])]
D3=[k('D3.01 – Tổng tin hiện tại',Q,COUNT),k('D3.02 – Thiếu giá',Q,'SUM(missing_price)'),k('D3.03 – Nghi trùng',Q,'SUM(suspected_duplicate)'),k('D3.04 – Tỷ lệ nhập thành công',B,'1.0 * SUM(accepted_rows)/NULLIF(SUM(total_rows),0)','.2%'),k('D3.05 – Lỗi nhập liệu',B,'SUM(error_count)'),spec('D3.06 – Tỷ lệ thiếu dữ liệu',Q,'echarts_timeseries_bar',[(f'AVG({c})',l) for c,l in [('missing_price','Giá'),('missing_area','Diện tích'),('missing_address','Địa chỉ'),('missing_district','Quận'),('missing_fee_info','Phí')]],x='data_origin',fmt='.0%'),spec('D3.07 – Chất lượng vị trí',Q,'pie',[(COUNT,'Số tin')],x='geo_confidence'),spec('D3.08 – Độ mới theo nguồn',Q,'echarts_timeseries_bar',[('AVG(freshness_hours)','Số giờ')],x='source_name'),spec('D3.09 – Kết quả nhập batch',B,'echarts_timeseries_bar',[('SUM(accepted_rows)','Thành công'),('SUM(rejected_rows)','Từ chối')],x='batch_id'),spec('D3.10 – Nhật ký nhập liệu',B,'table',cols=['batch_id','dataset_version','import_status','total_rows','accepted_rows','rejected_rows','acceptance_rate','error_count','imported_at'])]

class API:
    def __init__(self,url,user,password):
        self.url=url.rstrip('/')+'/api/v1'; self.s=requests.Session()
        r=self.call('POST','/security/login',json=dict(username=user,password=password,provider='db',refresh=True))
        self.s.headers['Authorization']='Bearer '+r['access_token']
        self.s.headers['X-CSRFToken']=self.call('GET','/security/csrf_token/')['result']
        self.s.headers['Referer']=url.rstrip('/')+'/'
    def call(self,method,path,**kw):
        r=self.s.request(method,self.url+path,timeout=90,**kw)
        if not r.ok: raise RuntimeError(f'{method} {path}: HTTP {r.status_code}' + ('' if path.startswith('/database') or path.startswith('/security') else ': '+r.text[:1500]))
        return r.json()
    def all(self,path):
        out=[]; page=0
        while True:
            r=self.call('GET',path,params={'q':f'(page:{page},page_size:100)'})
            rows=r['result']; out+=rows
            if not rows or len(out)>=r.get('count',len(out)): return out
            page+=1
    def upsert(self,path,existing,payload):
        if existing:
            self.call('PUT',f'{path}{existing["id"]}',json=payload); return existing['id']
        return self.call('POST',path,json=payload)['id']

def form(c,ds):
    filters=[filt('data_origin',[ORIGIN])]+c['extra']
    if c['ds'] in [P,A]: filters.append(filt('price_basis',['room']))
    f=dict(datasource=f'{ds}__table',viz_type=c['typ'],adhoc_filters=filters,time_range='No filter',row_limit=1000,color_scheme='supersetColors',number_format=c['fmt'],y_axis_format=c['fmt'],show_legend=True,show_value=True)
    if c['typ']=='big_number_total': f.update(metric=c['metrics'][0],y_axis_format=c['fmt'],subheader='')
    elif c['typ']=='table': f.update(query_mode='raw',all_columns=c['cols'],order_by_cols=[],page_length=15,include_search=True)
    elif c['typ']=='pie': f.update(metric=c['metrics'][0],groupby=[c['x']],donut=True,show_labels=True,label_type='key_percent')
    else: f.update(x_axis=c['x'],metrics=c['metrics'],groupby=[],orientation='vertical',x_axis_sort_asc=True,show_value=True,stack=None)
    return f

def layout(rows,charts,title):
    p={'DASHBOARD_VERSION_KEY':'v2','ROOT_ID':{'id':'ROOT_ID','type':'ROOT','children':['GRID_ID']},'GRID_ID':{'id':'GRID_ID','type':'GRID','children':[],'parents':['ROOT_ID']},'HEADER_ID':{'id':'HEADER_ID','type':'HEADER','meta':{'text':title}}}
    for i,row in enumerate(rows):
        rid=f'ROW-{i+1}'; p['GRID_ID']['children'].append(rid)
        p[rid]=dict(id=rid,type='ROW',children=[],parents=['ROOT_ID','GRID_ID'],meta={'background':'BACKGROUND_TRANSPARENT'})
        for j in row:
            cid,name,cuuid,typ=charts[j]; key=f'CHART-{cid}'; p[rid]['children'].append(key)
            p[key]=dict(id=key,type='CHART',children=[],parents=['ROOT_ID','GRID_ID',rid],meta=dict(chartId=cid,sliceName=name,uuid=cuuid,width=12//len(row),height=18 if typ=='big_number_total' else 50 if typ=='table' else 40))
    return p

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--url',default='http://localhost:8088'); ap.add_argument('--user',default='admin'); ap.add_argument('--export',action='store_true'); ap.add_argument('--bootstrap',action='store_true',help='Create missing database connection and datasets'); args=ap.parse_args()
    api=API(args.url,args.user,os.getenv('SUPERSET_PASSWORD') or getpass.getpass('Superset password: '))
    dbs=[d for d in api.all('/database/') if d['database_name']==DB]
    if not dbs and args.bootstrap:
        password=os.getenv('BI_READER_PASSWORD') or getpass.getpass('PostgreSQL bi_reader password: ')
        uri='postgresql+psycopg2://bi_reader:'+quote(password,safe='')+'@phongtro_bi_db:5432/phongtro_bi_demo'
        api.call('POST','/database/',json={'database_name':DB,'sqlalchemy_uri':uri})
        dbs=[d for d in api.all('/database/') if d['database_name']==DB]
    if len(dbs)!=1: raise RuntimeError('Expected exactly one database named '+DB)
    dbid=dbs[0]['id']; datasets={}
    for d in api.all('/dataset/'):
        db=d.get('database') or {}; dbname=db.get('database_name') if isinstance(db,dict) else None
        if d.get('schema')=='analytics' and (dbname==DB or (isinstance(db,dict) and db.get('id')==dbid)):
            datasets[d['table_name']]=d['id']
    required={P,A,Q,B,'vw_listing_current'}
    if args.bootstrap:
        for table in sorted(required-datasets.keys()):
            datasets[table]=api.call('POST','/dataset/',json={'database':dbid,'schema':'analytics','table_name':table})['id']
    if required-datasets.keys(): raise RuntimeError(f'Missing datasets: {required-datasets.keys()}; found {datasets}')
    existing_charts=api.all('/chart/'); existing_dash=api.all('/dashboard/'); ids=[]
    for slug,title,defs,rows,accent in [
        ('phongtro-market','PHONGTRO BI | 01 – Giá thuê',D1,[[0,1,2],[3,4,5],[6,7],[8],[9]],'#b65b91'),
        ('phongtro-affordability','PHONGTRO BI | 02 – Khả năng chi trả',D2,[[0,1,2],[3,4,5],[6],[7,8],[9]],'#348477'),
        ('phongtro-quality','PHONGTRO BI | 03 – Chất lượng dữ liệu',D3,[[0,1,2],[3,4],[5],[6,7],[8],[9]],'#8062b4')]:
        old=next((d for d in existing_dash if d.get('slug')==slug),None)
        did=api.upsert('/dashboard/',old,dict(dashboard_title=title,slug=slug,published=True)); ids.append(did)
        charts=[]
        owned=set()
        if old:
            detail=api.call('GET',f'/dashboard/{did}')['result']
            pos=detail.get('position_json') or '{}'
            pos=json.loads(pos) if isinstance(pos,str) else pos
            owned={v.get('meta',{}).get('chartId') for v in pos.values() if isinstance(v,dict) and v.get('type')=='CHART'}
        for c in defs:
            legacy='[PhongTro Auto] '+c['name']; name=c['name'].split(' – ',1)[-1]; ds=datasets[c['ds']]
            matches=[v for v in existing_charts if v.get('slice_name')==legacy or (v.get('id') in owned and v.get('slice_name')==name)]
            if len(matches)>1: raise RuntimeError('Duplicate chart: '+name)
            cid=api.upsert('/chart/',matches[0] if matches else None,dict(slice_name=name,viz_type=c['typ'],datasource_id=ds,datasource_type='table',params=json.dumps(form(c,ds),ensure_ascii=False),dashboards=[did]))
            detail=api.call('GET',f'/chart/{cid}')['result']; charts.append((cid,name,detail.get('uuid',''),c['typ'])); print('Chart',cid,name,flush=True)
        native=[]
        for col,label in [('district','Khu vực'),('source_name','Nguồn'),('room_type','Loại phòng')]:
            ds=datasets[defs[0]['ds']]; excluded=[charts[i][0] for i,c in enumerate(defs) if c['ds']==B]
            native.append(dict(id='NATIVE_FILTER-'+uuid.uuid5(uuid.NAMESPACE_URL,slug+col).hex,name=label,filterType='filter_select',targets=[dict(datasetId=ds,column={'name':col})],defaultDataMask={'extraFormData':{},'filterState':{}},controlValues={'multiSelect':True,'enableEmptyFilter':False,'searchAllOptions':False,'inverseSelection':False},cascadeParentIds=[],scope={'rootPath':['ROOT_ID'],'excluded':excluded},type='NATIVE_FILTER',description=''))
        css=(BASE/'dashboard.css').read_text(encoding='utf-8').replace('ACCENT_COLOR',accent)
        metadata=dict(native_filter_configuration=native,refresh_frequency=0,timed_refresh_immune_slices=[],expanded_slices={},label_colors={},color_scheme='supersetColors',cross_filters_enabled=False)
        api.call('PUT',f'/dashboard/{did}',json=dict(position_json=json.dumps(layout(rows,charts,title),ensure_ascii=False),json_metadata=json.dumps(metadata,ensure_ascii=False),css=css,published=True))
        print('Dashboard:',args.url+'/superset/dashboard/'+slug+'/',flush=True)
    if args.export:
        dest=BASE/'exports'; dest.mkdir(exist_ok=True)
        r=api.s.get(api.url+'/dashboard/export/',params={'q':'!('+','.join(map(str,ids))+')'},timeout=120); r.raise_for_status()
        if not r.content.startswith(b'PK'): raise RuntimeError('Export did not return ZIP')
        (dest/'phongtro_dashboards.zip').write_bytes(r.content)
        print('Export saved; inspect for secrets before committing.')
if __name__=='__main__': main()
