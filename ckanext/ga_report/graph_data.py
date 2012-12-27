import calendar
import datetime
import ckan.model as model
from ga_model import (GA_Url, GA_Stat, GA_ReferralStat, GA_Publisher)

def _date_for_period_name(period_name, period_day):
    year,month = map(int,period_name.split('-'))
    _, last_day_of_month = calendar.monthrange(year, month)
    #last_day_of_month = last_day_of_month / 2
    #if last_day_of_month % 2 != 0:
    #    last_day_of_month = last_day_of_month + 1
    dt = datetime.datetime(year=year, month=month,
                           day=period_day or last_day_of_month)
    return round(float(dt.strftime('%s.%f')),3)

def _graph_totals(month, title, key):
    data = [{
            'name': title,
            'color': 'steelblue',
            'data': []
            }]

    query = model.Session.query(GA_Stat).\
            filter(GA_Stat.stat_name=='Totals').\
            filter(GA_Stat.key==key).\
            order_by('ga_stat.period_name')

    for entry in query.all():
        data[0]['data'].append({'x': _date_for_period_name(entry.period_name,0),
                                'y': float(entry.value)})
    return data

CHARTS = {
    'totals': (_graph_totals,'Average time on site (in seconds)', 'Average time on site',),
    'bounce': (_graph_totals,'Bounce rate %', 'Bounce rate (home page)',),
    'new_visits': (_graph_totals,'New visits %', 'New visits',),
    'total_pageviews': (_graph_totals,'Total page views', 'Total page views',),
    'total_visits': (_graph_totals,'Total visits', 'Total visits',),
    'pages_per_visit': (_graph_totals,'Pages per visit', 'Pages per visit',),
}
