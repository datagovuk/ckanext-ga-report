import logging
import operator
from ckan.lib.base import BaseController, c, render,request

import ckan.model as model
from ga_model import GA_Url

log = logging.getLogger('ckanext.ga-report')

class GaReport(BaseController):

    def index(self):
        return render('ga_report/site/index.html')


class GaPublisherReport(BaseController):
    """
    Displays the pageview and visit count for specific publishers based on
    the datasets associated with the publisher.
    """

    def _get_month_name(self, str):
        import calendar
        from time import strptime
        d = strptime('2012-10', '%Y-%m')
        return '%s %s' % (calendar.month_name[d.tm_mon], d.tm_year)


    def index(self, id):
        c.publisher = model.Group.get(id)
        c.top_packages = [] # package, dataset_views in c.top_packages

        # Get the month details by fetching distinct values and determining the
        # month names from the values.
        c.months = []
        vals = model.Session.query(GA_Url.period_name).distinct().all()
        for m in vals:
            c.months.append( (m[0],self._get_month_name(m)))

        # Sort the months, so most recent is at the head of our list
        c.months = sorted(c.months, key=operator.itemgetter(0), reverse=True)

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
            order_by('ga_url.pageviews desc').all()
        for entry in entries:
            if entry.url.startswith('/dataset/'):
                p = model.Package.get(entry.url[len('/dataset/'):])
                c.top_packages.append((p,entry.pageviews,entry.visitors))

        return render('ga_report/publisher/index.html')
