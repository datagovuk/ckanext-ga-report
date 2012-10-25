import logging
import operator
from ckan.lib.base import BaseController, c, render, request, response

import sqlalchemy
from sqlalchemy import func, cast, Integer
import ckan.model as model
from ga_model import GA_Url, GA_Stat

log = logging.getLogger('ckanext.ga-report')


def _get_month_name(strdate):
    import calendar
    from time import strptime
    d = strptime(strdate, '%Y-%m')
    return '%s %s' % (calendar.month_name[d.tm_mon], d.tm_year)


def _month_details(cls):
    months = []
    vals = model.Session.query(cls.period_name).distinct().all()
    for m in vals:
        months.append( (m[0], _get_month_name(m[0])))
    return sorted(months, key=operator.itemgetter(0), reverse=True)


class GaReport(BaseController):

    def csv(self, month):
        import csv

        entries = model.Session.query(GA_Stat).\
            filter(GA_Stat.period_name==month).\
            order_by('GA_Stat.stat_name, GA_Stat.key').all()

        #response.headers['Content-disposition'] = 'attachment; filename=dgu_analytics_%s.csv' % (month,)
        response.headers['Content-Type'] = "text/csv; charset=utf-8"

        writer = csv.writer(response)
        writer.writerow(["Period", "Statistic", "Key", "Value"])

        for entry in entries:
            writer.writerow([entry.period_name.encode('utf-8'),
                             entry.stat_name.encode('utf-8'),
                             entry.key.encode('utf-8'),
                             entry.value.encode('utf-8')])

    def index(self):

        # Get the month details by fetching distinct values and determining the
        # month names from the values.
        c.months = _month_details(GA_Stat)

        # Work out which month to show, based on query params of the first item
        c.month = request.params.get('month', c.months[0][0] if c.months else '')
        c.month_desc = ''.join([m[1] for m in c.months if m[0]==c.month])

        entries = model.Session.query(GA_Stat).\
            filter(GA_Stat.stat_name=='Totals').\
            filter(GA_Stat.period_name==c.month).\
            order_by('ga_stat.key').all()
        c.global_totals = [(s.key, s.value) for s in entries ]

        keys = {
            'Browser versions': 'browsers',
            'Operating Systems versions': 'os',
            'Social sources': 'social_networks',
            'Languages': 'languages',
            'Country': 'country'
        }

        for k, v in keys.iteritems():
            entries = model.Session.query(GA_Stat).\
                filter(GA_Stat.stat_name==k).\
                filter(GA_Stat.period_name==c.month).\
                order_by('ga_stat.value::int desc').all()
            setattr(c, v, [(s.key, s.value) for s in entries ])


        return render('ga_report/site/index.html')


class GaPublisherReport(BaseController):
    """
    Displays the pageview and visit count for specific publishers based on
    the datasets associated with the publisher.
    """

    def index(self):

        # Get the month details by fetching distinct values and determining the
        # month names from the values.
        c.months = _month_details(GA_Url)

        # Work out which month to show, based on query params of the first item
        c.month = request.params.get('month', c.months[0][0] if c.months else '')
        c.month_desc = ''.join([m[1] for m in c.months if m[0]==c.month])

        connection = model.Session.connection()
        q = """
            select department_id, sum(pageviews::int) views, sum(visitors::int) visits
            from ga_url
            where department_id <> ''
                and not url like '/publisher/%%'
                and period_name=%s
            group by department_id order by views desc limit 20;
        """
        c.top_publishers = []
        res = connection.execute(q, c.month)
        for row in res:
            c.top_publishers.append((model.Group.get(row[0]), row[1], row[2]))

        return render('ga_report/publisher/index.html')


    def read(self, id):
        c.publisher = model.Group.get(id)
        c.top_packages = [] # package, dataset_views in c.top_packages

        # Get the month details by fetching distinct values and determining the
        # month names from the values.
        c.months = _month_details(GA_Url)

        # Work out which month to show, based on query params of the first item
        c.month = request.params.get('month', c.months[0][0] if c.months else '')
        c.month_desc = ''.join([m[1] for m in c.months if m[0]==c.month])

        entry = model.Session.query(GA_Url).\
            filter(GA_Url.url=='/publisher/%s' % c.publisher.name).\
            filter(GA_Url.period_name==c.month).first()
        c.publisher_page_views = entry.pageviews if entry else 0

        entries = model.Session.query(GA_Url).\
            filter(GA_Url.department_id==c.publisher.name).\
            filter(GA_Url.period_name==c.month).\
            order_by('ga_url.pageviews::int desc')[:20]
        for entry in entries:
            if entry.url.startswith('/dataset/'):
                p = model.Package.get(entry.url[len('/dataset/'):])
                c.top_packages.append((p,entry.pageviews,entry.visitors))

        return render('ga_report/publisher/read.html')
