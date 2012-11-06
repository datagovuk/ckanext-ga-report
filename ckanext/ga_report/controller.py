import re
import csv
import sys
import logging
import operator
import collections
from ckan.lib.base import (BaseController, c, g, render, request, response, abort)

import sqlalchemy
from sqlalchemy import func, cast, Integer
import ckan.model as model
from ga_model import GA_Url, GA_Stat, GA_ReferralStat

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

        q = model.Session.query(GA_Stat)
        if month != 'all':
            q = q.filter(GA_Stat.period_name==month)
        entries = q.order_by('GA_Stat.period_name, GA_Stat.stat_name, GA_Stat.key').all()

        response.headers['Content-Type'] = "text/csv; charset=utf-8"
        response.headers['Content-Disposition'] = str('attachment; filename=stats_%s.csv' % (month,))

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
        c.month_desc = 'all months'
        c.month = request.params.get('month', '')
        if c.month:
            c.month_desc = ''.join([m[1] for m in c.months if m[0]==c.month])

        q = model.Session.query(GA_Stat).\
            filter(GA_Stat.stat_name=='Totals')
        if c.month:
            q = q.filter(GA_Stat.period_name==c.month)
        entries = q.order_by('ga_stat.key').all()

        def clean_key(key, val):
            if key in ['Average time on site', 'Pages per visit', 'New visits', 'Bounces']:
                val =  "%.2f" % round(float(val), 2)
                if key == 'Average time on site':
                    mins, secs = divmod(float(val), 60)
                    hours, mins = divmod(mins, 60)
                    val = '%02d:%02d:%02d (%s seconds) ' % (hours, mins, secs, val)
                if key in ['New visits','Bounces']:
                    val = "%s%%" % val
            if key in ['Total page views', 'Total visits']:
                val = int(val)

            return key, val

        c.global_totals = []
        if c.month:
            for e in entries:
                key, val = clean_key(e.key, e.value)
                c.global_totals.append((key, val))
        else:
            d = collections.defaultdict(list)
            for e in entries:
                d[e.key].append(float(e.value))
            for k, v in d.iteritems():
                if k in ['Total page views', 'Total visits']:
                    v = sum(v)
                else:
                    v = float(sum(v))/len(v)
                key, val = clean_key(k,v)

                c.global_totals.append((key, val))
                c.global_totals = sorted(c.global_totals, key=operator.itemgetter(0))

        keys = {
            'Browser versions': 'browser_versions',
            'Browsers': 'browsers',
            'Operating Systems versions': 'os_versions',
            'Operating Systems': 'os',
            'Social sources': 'social_networks',
            'Languages': 'languages',
            'Country': 'country'
        }

        def shorten_name(name, length=60):
            return (name[:length] + '..') if len(name) > 60 else name

        def fill_out_url(url):
            import urlparse
            return urlparse.urljoin(g.site_url, url)

        c.social_referrer_totals, c.social_referrers = [], []
        q = model.Session.query(GA_ReferralStat)
        q = q.filter(GA_ReferralStat.period_name==c.month) if c.month else q
        q = q.order_by('ga_referrer.count::int desc')
        for entry in q.all():
            c.social_referrers.append((shorten_name(entry.url), fill_out_url(entry.url),
                                       entry.source,entry.count))

        q = model.Session.query(GA_ReferralStat.url,
                                func.sum(GA_ReferralStat.count).label('count'))
        q = q.filter(GA_ReferralStat.period_name==c.month) if c.month else q
        q = q.order_by('count desc').group_by(GA_ReferralStat.url)
        for entry in q.all():
            c.social_referrer_totals.append((shorten_name(entry[0]), fill_out_url(entry[0]),'',
                                            entry[1]))


        browser_version_re = re.compile("(.*)\((.*)\)")
        for k, v in keys.iteritems():

            def clean_field(key):
                if k != 'Browser versions':
                    return key
                m = browser_version_re.match(key)
                browser = m.groups()[0].strip()
                ver = m.groups()[1]
                parts = ver.split('.')
                if len(parts) > 1:
                    if parts[1][0] == '0':
                        ver = parts[0]
                    else:
                        ver = "%s.%s" % (parts[0],parts[1])
                if browser in ['Safari','Android Browser']:  # Special case complex version nums
                    ver = parts[0]
                    if len(ver) > 2:
                        ver = "%s%sX" % (ver[0], ver[1])

                return "%s (%s)" % (browser, ver,)

            q = model.Session.query(GA_Stat).\
                filter(GA_Stat.stat_name==k)
            if c.month:
                entries = []
                q = q.filter(GA_Stat.period_name==c.month).\
                          order_by('ga_stat.value::int desc')

            d = collections.defaultdict(int)
            for e in q.all():
                d[clean_field(e.key)] += int(e.value)
            entries = []
            for key, val in d.iteritems():
                entries.append((key,val,))
            entries = sorted(entries, key=operator.itemgetter(1), reverse=True)

            # Get the total for each set of values and then set the value as
            # a percentage of the total
            if k == 'Social sources':
                total = sum([x for n,x in c.global_totals if n == 'Total visits'])
            else:
                total = sum([num for _,num in entries])
            setattr(c, v, [(k,_percent(v,total)) for k,v in entries ])

        return render('ga_report/site/index.html')


class GaPublisherReport(BaseController):
    """
    Displays the pageview and visit count for specific publishers based on
    the datasets associated with the publisher.
    """
    def csv(self, month):

        c.month = month if not month =='all' else ''
        response.headers['Content-Type'] = "text/csv; charset=utf-8"
        response.headers['Content-Disposition'] = str('attachment; filename=publishers_%s.csv' % (month,))

        writer = csv.writer(response)
        writer.writerow(["Publisher", "Views", "Visits", "Period Name"])

        for publisher,view,visit in _get_publishers(None):
            writer.writerow([publisher.title.encode('utf-8'),
                             view,
                             visit,
                             month])



    def publisher_csv(self, id, month):

        c.month = month if not month =='all' else ''
        c.publisher = model.Group.get(id)
        if not c.publisher:
            abort(404, 'A publisher with that name could not be found')

        packages = self._get_packages(c.publisher)
        response.headers['Content-Type'] = "text/csv; charset=utf-8"
        response.headers['Content-Disposition'] = \
            str('attachment; filename=%s_%s.csv' % (c.publisher.name, month,))

        writer = csv.writer(response)
        writer.writerow(["Publisher", "Views", "Visits", "Period Name"])

        for package,view,visit in packages:
            writer.writerow([package.title.encode('utf-8'),
                             view,
                             visit,
                             month])



    def index(self):

        # Get the month details by fetching distinct values and determining the
        # month names from the values.
        c.months = _month_details(GA_Url)

        # Work out which month to show, based on query params of the first item
        c.month = request.params.get('month', '')
        c.month_desc = 'all months'
        if c.month:
            c.month_desc = ''.join([m[1] for m in c.months if m[0]==c.month])

        c.top_publishers = _get_publishers()

        return render('ga_report/publisher/index.html')


    def _get_packages(self, publisher, count=-1):
        if count == -1:
            count = sys.maxint

        top_packages = []
        q =  model.Session.query(GA_Url).\
            filter(GA_Url.department_id==publisher.name).\
            filter(GA_Url.url.like('/dataset/%'))
        if c.month:
            q = q.filter(GA_Url.period_name==c.month)
        q = q.order_by('ga_url.pageviews::int desc')

        if c.month:
            for entry in q[:count]:
                p = model.Package.get(entry.url[len('/dataset/'):])
                top_packages.append((p,entry.pageviews,entry.visitors))
        else:
            ds = {}
            for entry in q.all():
                if len(ds) >= count:
                    break
                p = model.Package.get(entry.url[len('/dataset/'):])
                if not p in ds:
                    ds[p] = {'views':0, 'visits': 0}
                ds[p]['views'] = ds[p]['views'] + int(entry.pageviews)
                ds[p]['visits'] = ds[p]['visits'] + int(entry.visitors)

            results = []
            for k, v in ds.iteritems():
                results.append((k,v['views'],v['visits']))

            top_packages = sorted(results, key=operator.itemgetter(1), reverse=True)
        return top_packages


    def read(self, id):
        count = 20

        c.publisher = model.Group.get(id)
        if not c.publisher:
            abort(404, 'A publisher with that name could not be found')
        c.top_packages = [] # package, dataset_views in c.top_packages

        # Get the month details by fetching distinct values and determining the
        # month names from the values.
        c.months = _month_details(GA_Url)

        # Work out which month to show, based on query params of the first item
        c.month = request.params.get('month', '')
        if not c.month:
            c.month_desc = 'all months'
        else:
            c.month_desc = ''.join([m[1] for m in c.months if m[0]==c.month])

        c.publisher_page_views = 0
        q = model.Session.query(GA_Url).\
            filter(GA_Url.url=='/publisher/%s' % c.publisher.name)
        if c.month:
            entry = q.filter(GA_Url.period_name==c.month).first()
            c.publisher_page_views = entry.pageviews if entry else 0
        else:
            for e in q.all():
                c.publisher_page_views = c.publisher_page_views  + int(e.pageviews)

        c.top_packages = self._get_packages(c.publisher, 20)

        return render('ga_report/publisher/read.html')

def _get_publishers(limit=20):
    connection = model.Session.connection()
    q = """
        select department_id, sum(pageviews::int) views, sum(visitors::int) visits
        from ga_url
        where department_id <> ''"""
    if c.month:
        q = q + """
                and period_name=%s
        """
    q = q + """
            group by department_id order by views desc
        """
    if limit:
        q = q + " limit %s;" % (limit)

    # Add this back (before and period_name =%s) if you want to ignore publisher
    # homepage views
    # and not url like '/publisher/%%'

    top_publishers = []
    res = connection.execute(q, c.month)

    for row in res:
        g = model.Group.get(row[0])
        if g:
            top_publishers.append((g, row[1], row[2]))
    return top_publishers


def _percent(num, total):
    p = 100 * float(num)/float(total)
    return "%.2f%%" % round(p, 2)
