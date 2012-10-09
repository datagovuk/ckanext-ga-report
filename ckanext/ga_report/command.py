import logging

from ckan.lib.cli import CkanCommand
# No other CKAN imports allowed until _load_config is run, or logging is disabled

class InitDB(CkanCommand):
    """Initialise the extension's database tables
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        log = logging.getLogger('ckanext.ga-report')

        import ga_model
        ga_model.init_tables()
        log.info("DB tables are setup")


class GetAuthToken(CkanCommand):
    """ Get's the Google auth token
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        from ga_auth import initialize_service
        initialize_service('token.dat',
                           self.args[0] if self.args
                                        else 'credentials.json')

class LoadAnalytics(CkanCommand):
    """Get data from Google Analytics API and save it
    in the ga_model

    Usage: paster loadanalytics <tokenfile> <time-period>

    Where <tokenfile> is the name of the auth token file from
    the getauthtoken step.

    And where <time-period> is:
        all         - data for all time
        latest      - (default) just the 'latest' data
        YYYY-MM-DD  - just data for all time periods going
                      back to (and including) this date
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 1

    def command(self):
        self._load_config()

        from ga_auth import initialize_service
        try:
            svc = initialize_service(self.args[0], None)
        except TypeError:
            print 'Have you correctly run the getauthtoken task and specified the correct file here'
            return

        from download_analytics import DownloadAnalytics
        from ga_auth import get_profile_id
        downloader = DownloadAnalytics(svc, profile_id=get_profile_id(svc))

        time_period = self.args[1] if self.args and len(self.args) > 1 else 'latest'
        if time_period == 'all':
            downloader.all_()
        elif time_period == 'latest':
            downloader.latest()
        else:
            since_date = datetime.datetime.strptime(time_period, '%Y-%m-%d')
            downloader.since_date(since_date)

