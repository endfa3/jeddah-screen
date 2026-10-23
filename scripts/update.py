import json, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
now = datetime.now(timezone(timedelta(hours=3)))
today = now.date()
path = ROOT / 'data/dashboard.json'
data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
def get(url, raw=False):
    req = urllib.request.Request(url, headers={'User-Agent':'JeddahPersonalDashboard/1.0'})
    with urllib.request.urlopen(req, timeout=25) as response:
        value = response.read()
    return value if raw else json.loads(value)
def weather():
    result = get('https://api.open-meteo.com/v1/forecast?latitude=21.5433&longitude=39.1728&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m&timezone=Asia%2FRiyadh')
    return {'current':result['current']}
def prayer():
    def fetch(d):
        return get(f'https://api.aladhan.com/v1/timingsByCity/{d:%d-%m-%Y}?city=Jeddah&country=Saudi%20Arabia&method=4')['data']['timings']
    tomorrow = today + timedelta(days=1)
    return {'date':str(today),'timings':fetch(today),'tomorrowDate':str(tomorrow),'tomorrowFajr':fetch(tomorrow)['Fajr']}
TEAMS={'Al Ittihad':'الاتحاد','Al Hilal':'الهلال','Al Nassr':'النصر','Al Ahli':'الأهلي','Al Shabab':'الشباب','Al Taawoun':'التعاون','Al Ettifaq':'الاتفاق','Real Madrid':'ريال مدريد','Barcelona':'برشلونة','Liverpool':'ليفربول','Arsenal':'أرسنال','Manchester City':'مانشستر سيتي','Manchester United':'مانشستر يونايتد','Chelsea':'تشيلسي','Tottenham Hotspur':'توتنهام'}
TEAMS.update({'Al Faisaly':'الفيصلي','Al Diriyah':'الدرعية','Al Khaleej':'الخليج','Al Qadsiah':'القادسية','Ipswich Town':'إيبسويتش تاون','Nottingham Forest':'نوتنغهام فورست','Alavés':'ألافيس','Málaga':'ملقا','Al Fateh':'الفتح','Al Riyadh':'الرياض','Al Fayha':'الفيحاء','Al Hazem':'الحزم','Al Okhdood':'الأخدود','Damac':'ضمك','Neom SC':'نيوم','Al Najma':'النجمة'})
def matches():
    items=[]; errors=[]
    for league,label in [('ksa.1','السعودي'),('eng.1','الإنجليزي'),('esp.1','الإسباني'),('uefa.champions','أبطال أوروبا')]:
        try:
            start=today-timedelta(days=1)
            result={'events':[]}
            for date in [start,today]:
                result['events'].extend(get(f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date:%Y%m%d}&limit=100').get('events',[]))
            for e in result.get('events',[]):
                if datetime.fromisoformat(e['date'].replace('Z','+00:00')).astimezone(now.tzinfo).date()!=today: continue
                c=e['competitions'][0]; sides={x['homeAway']:x for x in c['competitors']}; h=sides['home'];a=sides['away']
                name=lambda x: TEAMS.get(x['team']['displayName'],x['team']['displayName'])
                items.append({'id':e['id'],'date':e['date'],'home':name(h),'away':name(a),'homeScore':h.get('score','0'),'awayScore':a.get('score','0'),'state':e['status']['type']['state'],'league':label})
        except Exception as ex: errors.append(league); print('Match source unavailable:',league,type(ex).__name__)
    if len(errors)==4: raise RuntimeError('All match feeds unavailable')
    unique={m['id']:m for m in items}
    return {'date':str(today),'items':sorted(unique.values(),key=lambda m:m['date']),'error':bool(errors)}
def news():
    items=[]
    for url,label in [('https://www.tech-wd.com/wd/feed/','عالم التقنية'),('https://aitnews.com/feed/','البوابة التقنية')]:
        try:
            root=ET.fromstring(get(url,True))
            for item in root.findall('.//item')[:5]:
                title=item.findtext('title','').strip(); link=item.findtext('link','').strip()
                if title and link.startswith('https://'): items.append({'title':title,'link':link,'source':label})
        except Exception as ex: print('News source unavailable:',label,type(ex).__name__)
    if not items: raise RuntimeError('News feeds unavailable')
    return {'items':items}
def run(pair):
    key,fn=pair
    try: return key,{**fn(),'updated':now.isoformat()}
    except Exception as ex:
        print(key,'unavailable:',type(ex).__name__)
        return key,{**data.get(key,{}),'error':True}
with ThreadPoolExecutor(max_workers=4) as pool:
    for key,value in pool.map(run,[('weather',weather),('prayer',prayer),('matches',matches),('news',news)]): data[key]=value
data['generated']=now.isoformat()
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Updated:', ', '.join(k for k in ['weather','prayer','matches','news'] if not data[k].get('error')))
