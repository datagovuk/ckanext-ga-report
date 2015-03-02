import logging
import datetime
import os

from pylons import config

from ckan.lib.cli import CkanCommand
# No other CKAN imports allowed until _load_config is run,
# or logging is disabled


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
        log = logging.getLogger('ckanext.ga_report')

        import ga_model
        ga_model.init_tables()
        log.info("DB tables are setup")


class GetAuthToken(CkanCommand):
    """ Gets the auth token from Google and saves it as token.dat.

    Usage: paster getauthtoken <credentials_file>

    Where <credentials_file> is the file name containing the details
    of your client authorized for your Google Analytics data
    (known as credentials.json or client_secrets.json)
    which is obtained from https://code.google.com/apis/console.
    By default this is set to credentials.json
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def command(self):
        """
        In this case we don't want a valid service, but rather just to
        force the user through the auth flow. We allow this to complete to
        act as a form of verification instead of just getting the token and
        assuming it is correct.
        """
        from ga_auth import init_service
        init_service('token.dat',
                      self.args[0] if self.args
                                   else 'credentials.json')

class FixTimePeriods(CkanCommand):
    """
    Fixes the 'All' records for GA_Urls

    It is possible that older urls that haven't recently been visited
    do not have All records.  This command will traverse through those
    records and generate valid All records for them.
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def __init__(self, name):
        super(FixTimePeriods, self).__init__(name)

    def command(self):
        import ckan.model as model
        from ga_model import post_update_url_stats
        self._load_config()
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)

        log = logging.getLogger('ckanext.ga_report')

        log.info("Updating 'All' records for old URLs")
        post_update_url_stats(print_progress=True)
        log.info("Processing complete")



class LoadAnalytics(CkanCommand):
    """Get data from Google Analytics API and save it
    in the ga_model

    Usage: paster loadanalytics <time-period>

    Where <time-period> is:
        all         - data for all time
        latest      - (default) just the 'latest' data
        YYYY-MM     - just data for the specific month
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    def __init__(self, name):
        super(LoadAnalytics, self).__init__(name)
        self.stat_names = ('url', 'url-all', 'sitewide', 'social')
        self.parser.add_option('-d', '--delete-first',
                               action='store_true',
                               default=False,
                               dest='delete_first',
                               help='Delete data for the period first')
        self.parser.add_option('-s', '--stat',
                               metavar="STAT",
                               dest='stat',
                               help='Only calulcate a particular stat (or collection of stats)- one of: %s' %
                                    '|'.join(self.stat_names))
        self.token = ""

    def command(self):
        self._load_config()

        from download_analytics import DownloadAnalytics
        from ga_auth import (init_service, get_profile_id)

        ga_token_filepath = os.path.expanduser(config.get('googleanalytics.token.filepath', ''))
        if not ga_token_filepath:
            print 'ERROR: In the CKAN config you need to specify the filepath of the ' \
                  'Google Analytics token file under key: googleanalytics.token.filepath'
            return

        try:
            self.token, svc = init_service(ga_token_filepath, None)
        except TypeError:
            print ('Have you correctly run the getauthtoken task and '
                   'specified the correct token file in the CKAN config under '
                   '"googleanalytics.token.filepath"?')
            return

        downloader = DownloadAnalytics(svc, self.token, profile_id=get_profile_id(svc),
                                       delete_first=self.options.delete_first,
                                       stat=self.options.stat,
                                       print_progress=True)

        time_period = self.args[0] if self.args else 'latest'
        if time_period == 'all':
            downloader.all_()
        elif time_period == 'latest':
            downloader.latest()
        else:
            # The month to use
            for_date = datetime.datetime.strptime(time_period, '%Y-%m')
            downloader.specific_month(for_date)
