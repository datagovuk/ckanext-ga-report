import os
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

            data = self.download(start_date, end_date, '~/dataset/[a-z0-9-_]+')
            log.info('Storing Dataset Analytics for period "%s"',
                     self.get_full_period_name(period_name, period_complete_day))
            self.store(period_name, period_complete_day, data, )

            data = self.download(start_date, end_date, '~/publisher/[a-z0-9-_]+')
            log.info('Storing Publisher Analytics for period "%s"',
                     self.get_full_period_name(period_name, period_complete_day))
            self.store(period_name, period_complete_day, data,)

            ga_model.update_publisher_stats(period_name) # about 30 seconds.
            self.sitewide_stats( period_name )


    def download(self, start_date, end_date, path='~/dataset/[a-z0-9-_]+'):
        '''Get data from GA for a given time period'''
        start_date = start_date.strftime('%Y-%m-%d')
        end_date = end_date.strftime('%Y-%m-%d')
        query = 'ga:pagePath=%s$' % path
        metrics = 'ga:uniquePageviews, ga:visitors'
        sort = '-ga:uniquePageviews'

        # Supported query params at
        # https://developers.google.com/analytics/devguides/reporting/core/v3/reference
        results = self.service.data().ga().get(
                                 ids='ga:' + self.profile_id,
                                 filters=query,
                                 start_date=start_date,
                                 metrics=metrics,
                                 sort=sort,
                                 dimensions="ga:pagePath",
                                 max_results=10000,
                                 end_date=end_date).execute()

        if os.getenv('DEBUG'):
            import pprint
            pprint.pprint(results)
            print 'Total results: %s' % results.get('totalResults')

        packages = []
        for entry in results.get('rows'):
            (loc,pageviews,visits) = entry
            packages.append( ('http:/' + loc, pageviews, visits,) ) # Temporary hack
        return dict(url=packages)

    def store(self, period_name, period_complete_day, data):
        if 'url' in data:
            ga_model.update_url_stats(period_name, period_complete_day, data['url'])

    def sitewide_stats(self, period_name):
        import calendar
        year, month = period_name.split('-')
        _, last_day_of_month = calendar.monthrange(int(year), int(month))

        start_date = '%s-01' % period_name
        end_date = '%s-%s' % (period_name, last_day_of_month)
        print 'Sitewide_stats for %s (%s -> %s)' % (period_name, start_date, end_date)

        funcs = ['_totals_stats', '_social_stats', '_os_stats',
                 '_locale_stats', '_browser_stats', '_mobile_stats']
        for f in funcs:
            print ' + Fetching %s stats' % f.split('_')[1]
            getattr(self, f)(start_date, end_date, period_name)

    def _get_results(result_data, f):
        data = {}
        for result in result_data:
            key = f(result)
            data[key] = data.get(key,0) + result[1]
        return data

    def _totals_stats(self, start_date, end_date, period_name):
        """ Fetches distinct totals, total pageviews etc """
        results = self.service.data().ga().get(
                                 ids='ga:' + self.profile_id,
                                 start_date=start_date,
                                 metrics='ga:uniquePageviews',
                                 sort='-ga:uniquePageviews',
                                 max_results=10000,
                                 end_date=end_date).execute()
        result_data = results.get('rows')
        ga_model.update_sitewide_stats(period_name, "Totals", {'Total pageviews': result_data[0][0]})

        results = self.service.data().ga().get(
                                 ids='ga:' + self.profile_id,
                                 start_date=start_date,
                                 metrics='ga:pageviewsPerVisit,ga:bounces,ga:avgTimeOnSite,ga:percentNewVisits',
                                 max_results=10000,
                                 end_date=end_date).execute()
        result_data = results.get('rows')
        data = {
            'Pages per visit': result_data[0][0],
            'Bounces': result_data[0][1],
            'Average time on site': result_data[0][2],
            'Percent new visits': result_data[0][3],
        }
        ga_model.update_sitewide_stats(period_name, "Totals", data)


    def _locale_stats(self, start_date, end_date, period_name):
        """ Fetches stats about language and country """
        results = self.service.data().ga().get(
                                 ids='ga:' + self.profile_id,
                                 start_date=start_date,
                                 metrics='ga:uniquePageviews',
                                 sort='-ga:uniquePageviews',
                                 dimensions="ga:language,ga:country",
                                 max_results=10000,
                                 end_date=end_date).execute()
        result_data = results.get('rows')
        data = {}
        for result in result_data:
            data[result[0]] = data.get(result[0], 0) + int(result[2])
        ga_model.update_sitewide_stats(period_name, "Languages", data)

        data = {}
        for result in result_data:
            data[result[1]] = data.get(result[1], 0) + int(result[2])
        ga_model.update_sitewide_stats(period_name, "Country", data)


    def _social_stats(self, start_date, end_date, period_name):
        """ Finds out which social sites people are referred from """
        results = self.service.data().ga().get(
                                 ids='ga:' + self.profile_id,
                                 start_date=start_date,
                                 metrics='ga:uniquePageviews',
                                 sort='-ga:uniquePageviews',
                                 dimensions="ga:socialNetwork,ga:referralPath",
                                 max_results=10000,
                                 end_date=end_date).execute()
        result_data = results.get('rows')
        twitter_links = []
        data = {}
        for result in result_data:
            if not result[0] == '(not set)':
                data[result[0]] = data.get(result[0], 0) + int(result[2])
                if result[0] == 'Twitter':
                    twitter_links.append(result[1])
        ga_model.update_sitewide_stats(period_name, "Social sources", data)


    def _os_stats(self, start_date, end_date, period_name):
        """ Operating system stats """
        results = self.service.data().ga().get(
                                 ids='ga:' + self.profile_id,
                                 start_date=start_date,
                                 metrics='ga:uniquePageviews',
                                 sort='-ga:uniquePageviews',
                                 dimensions="ga:operatingSystem,ga:operatingSystemVersion",
                                 max_results=10000,
                                 end_date=end_date).execute()
        result_data = results.get('rows')
        data = {}
        for result in result_data:
            data[result[0]] = data.get(result[0], 0) + int(result[2])
        ga_model.update_sitewide_stats(period_name, "Operating Systems", data)

        data = {}
        for result in result_data:
            key = "%s (%s)" % (result[0],result[1])
            data[key] = result[2]
        ga_model.update_sitewide_stats(period_name, "Operating Systems versions", data)


    def _browser_stats(self, start_date, end_date, period_name):
        """ Information about browsers and browser versions """
        results = self.service.data().ga().get(
                                 ids='ga:' + self.profile_id,
                                 start_date=start_date,
                                 metrics='ga:uniquePageviews',
                                 sort='-ga:uniquePageviews',
                                 dimensions="ga:browser,ga:browserVersion",
                                 max_results=10000,
                                 end_date=end_date).execute()
        result_data = results.get('rows')
        data = {}
        for result in result_data:
            data[result[0]] = data.get(result[0], 0) + int(result[2])
        ga_model.update_sitewide_stats(period_name, "Browsers", data)

        data = {}
        for result in result_data:
            key = "%s (%s)" % (result[0], result[1])
            data[key] = result[2]
        ga_model.update_sitewide_stats(period_name, "Browser versions", data)


    def _mobile_stats(self, start_date, end_date, period_name):
        """ Info about mobile devices """

        results = self.service.data().ga().get(
                                 ids='ga:' + self.profile_id,
                                 start_date=start_date,
                                 metrics='ga:uniquePageviews',
                                 sort='-ga:uniquePageviews',
                                 dimensions="ga:mobileDeviceBranding, ga:mobileDeviceInfo",
                                 max_results=10000,
                                 end_date=end_date).execute()

        result_data = results.get('rows')
        data = {}
        for result in result_data:
            data[result[0]] = data.get(result[0], 0) + int(result[2])
        ga_model.update_sitewide_stats(period_name, "Mobile brands", data)

        data = {}
        for result in result_data:
            data[result[1]] = data.get(result[1], 0) + int(result[2])
        ga_model.update_sitewide_stats(period_name, "Mobile devices", data)
