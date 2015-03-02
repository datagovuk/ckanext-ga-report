import os
import httplib2
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run

from pylons import config

log = __import__('logging').getLogger(__name__)


def _prepare_credentials(token_filename, credentials_filename):
    """
    Either returns the user's oauth credentials or uses the credentials
    file to generate a token (by forcing the user to login in the browser)
    """
    storage = Storage(token_filename)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        flow = flow_from_clientsecrets(credentials_filename,
            scope='https://www.googleapis.com/auth/analytics.readonly')
        credentials = run(flow, storage)

    return credentials


def init_service(token_file, credentials_file):
    """
    Given a file containing the user's oauth token (and another with
    credentials in case we need to generate the token) will return a
    service object representing the analytics API.

    On error, GA appears to raise TypeError.
    """
    http = httplib2.Http()

    credentials = _prepare_credentials(token_file, credentials_file)
    http = credentials.authorize(http)  # authorize the http object

    service = credentials.access_token, build('analytics', 'v3', http=http)
    return service


def get_profile_id(service):
    """
    Returns the GA Profile ID (a number), which is derived from the GA Property
    ID (e.g. 'UA-10855508-6'), as specified by configured googleananalyics.id.
    It also checks that that Property ID exists for the configured
    googleanalytics.account and is accessible with the OAuth token.
    """
    # Get list of GA Accounts available to the GA user represented by the OAuth
    # token
    accounts = service.management().accounts().list().execute()
    if not accounts.get('items'):
        log.error('No GA accounts are associated with the GA user (OAuth token)')
        return None

    # Check the config of the GA Account (googleanalytics.account)
    accountName = config.get('googleanalytics.account')
    if not accountName:
        raise Exception('googleanalytics.account needs to be configured')
    accounts_by_name = dict([(acc.get('name'), acc.get('id'))
                             for acc in accounts.get('items', [])])
    if accountName not in accounts_by_name:
        log.error('The specified GA account is not available. Configure googleanalytics.account to one of: %r', accounts_by_name.keys())
        return None
    accountId = accounts_by_name[accountName]  # e.g. accountId='10855508'

    # Check the config of the GA Property ID (googleanalyics.id)
    webproperties = service.management().webproperties().list(accountId=accountId).execute()
    property_ids = [prop.get('id') for prop in webproperties.get('items', [])]
    webPropertyId = config.get('googleanalytics.id')
    if not webPropertyId:
        raise Exception('googleanalytics.id needs to be configured')
    if webPropertyId not in property_ids:
        log.error('The specified GA Property is not available. Configure googleanalytics.id to one of: %r', property_ids.keys())
        return None

    # Convert the GA Property ID to GA's internal number "Profile ID"
    profiles = service.management().profiles().list(
        accountId=accountId, webPropertyId=webPropertyId).execute()
    if not profiles.get('items'):
        log.error('The specified GA Property ID does not appear to have an internal profile.Check config of googleanalytics.id')
        return None
    profileId = profiles['items'][0]['id']

    log.debug('GA Property %s has GA Profile id: %s', webPropertyId, profileId)
    return profileId

