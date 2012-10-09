import httplib2
from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run

from pylons import config


def _prepare_credentials( token_filename, credentials_filename ):
    storage = Storage( token_filename )
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        flow = flow_from_clientsecrets(credentials_filename,
                scope='https://www.googleapis.com/auth/analytics.readonly',
                message="Can't find the credentials file")
        credentials = run(flow, storage)

    return credentials

def initialize_service( token_file, credentials_file ):
    http = httplib2.Http()

    credentials = _prepare_credentials(token_file, credentials_file)
    http = credentials.authorize(http)  # authorize the http object

    return build('analytics', 'v3', http=http)

def get_profile_id(service):
    # Get a list of all Google Analytics accounts for this user
    accounts = service.management().accounts().list().execute()

    if accounts.get('items'):
        firstAccountId = accounts.get('items')[0].get('id')
        webPropertyId = config.get('googleanalytics.id')
        profiles = service.management().profiles().list(
                    accountId=firstAccountId,
                    webPropertyId=webPropertyId).execute()

        if profiles.get('items'):
            # return the first Profile ID
            return profiles.get('items')[0].get('id')

    return None