import logging
import datetime

from pylons import config

import ga_model

#from ga_client import GA

log = logging.getLogger('ckanext.ga-report')

FORMAT_MONTH = '%Y-%m'

class DownloadAnalytics(object):
    '''Downloads and stores analytics info'''

    def __init__(self, service=None, profile_id=None):
        self.period = config['ga-report.period']
        self.service = service
        self.profile_id = profile_id


    def all_(self):
        self.since_date(datetime.datetime(2010, 1, 1))

    def latest(self):
        if self.period == 'monthly':
            # from first of this month to today
            now = datetime.datetime.now()
            first_of_this_month = datetime.datetime(now.year, now.month, 1)
            periods = ((now.strftime(FORMAT_MONTH),
                        now.day,
                        first_of_this_month, now),)
        else:
            raise NotImplementedError
        self.download_and_store(periods)


    def since_date(self, since_date):
        assert isinstance(since_date, datetime.datetime)
        periods = [] # (period_name, period_complete_day, start_date, end_date)
        if self.period == 'monthly':
            first_of_the_months_until_now = []
            year = since_date.year
            month = since_date.month
            now = datetime.datetime.now()
            first_of_this_month = datetime.datetime(now.year, now.month, 1)
            while True:
                first_of_the_month = datetime.datetime(year, month, 1)
                if first_of_the_month == first_of_this_month:
                    periods.append((now.strftime(FORMAT_MONTH),
                                    now.day,
                                    first_of_this_month, now))
                    break
                elif first_of_the_month < first_of_this_month:
                    in_the_next_month = first_of_the_month + datetime.timedelta(40)
                    last_of_the_month = datetime.datetime(in_the_next_month.year,
                                                           in_the_next_month.month, 1)\
                                                           - datetime.timedelta(1)
                    periods.append((now.strftime(FORMAT_MONTH), 0,
                                    first_of_the_month, last_of_the_month))
                else:
                    # first_of_the_month has got to the future somehow
                    break
                month += 1
                if month > 12:
                    year += 1
                    month = 1
        else:
            raise NotImplementedError
        self.download_and_store(periods)

    @staticmethod
    def get_full_period_name(period_name, period_complete_day):
        if period_complete_day:
            return period_name + ' (up to %ith)' % period_complete_day
        else:
            return period_name


    def download_and_store(self, periods):
        for period_name, period_complete_day, start_date, end_date in periods:
            log.info('Downloading Analytics for period "%s" (%s - %s)',
                     self.get_full_period_name(period_name, period_complete_day),
                     start_date.strftime('%Y %m %d'),
                     end_date.strftime('%Y %m %d'))
            data = self.download(start_date, end_date)
            log.info('Storing Analytics for period "%s"',
                     self.get_full_period_name(period_name, period_complete_day))
            self.store(period_name, period_complete_day, data)


    def download(self, start_date, end_date):
        '''Get data from GA for a given time period'''
        start_date = start_date.strftime('%Y-%m-%d')
        end_date = end_date.strftime('%Y-%m-%d')
        # url
        #query = 'ga:pagePath=~^%s,ga:pagePath=~^%s' % \
        #        (PACKAGE_URL, self.resource_url_tag)
        query = 'ga:pagePath=~^/dataset/'
        #query = 'ga:pagePath=~^/User/'
        metrics = 'ga:uniquePageviews'
        sort = '-ga:uniquePageviews'

        # Supported query params at
        # https://developers.google.com/analytics/devguides/reporting/core/v3/reference
        results = self.service.data().ga().get(
                                 ids='ga:' + self.profile_id,
                                 filters=query,
                                 start_date=start_date,
                                 metrics=metrics,
                                 sort=sort,
                                 end_date=end_date).execute()
        self.print_results(results)

#        for entry in GA.ga_query(query_filter=query,
#                                 from_date=start_date,
#                                 metrics=metrics,
#                                 sort=sort,
#                                 to_date=end_date):
#            print entry, type(entry)
#            import pdb; pdb.set_trace()
#            for dim in entry.dimension:
#                if dim.name == "ga:pagePath":
#                    package = dim.value
#                    count = entry.get_metric(
#                        'ga:uniquePageviews').value or 0
#                    packages[package] = int(count)
        return []

    def print_results(self, results):
        import pprint
        pprint.pprint(results)
        if results:
            print 'Profile: %s' % results.get('profileInfo').get('profileName')
            print 'Total results: %s' % results.get('totalResults')
            print 'Total Visits: %s' % results.get('rows', [[-1]])[0][0]
        else:
            print 'No results found'

    def store(self, period_name, period_complete_day, data):
        if 'url' in data:
            ga_model.update_url_stats(period_name, period_complete_day, data['url'])
