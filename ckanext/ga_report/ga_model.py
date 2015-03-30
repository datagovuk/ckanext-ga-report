import re
import uuid

from sqlalchemy import Table, Column, MetaData
from sqlalchemy import types
from sqlalchemy.orm import mapper
from sqlalchemy.sql.expression import cast
from sqlalchemy import func

import ckan.model as model

from lib import GaProgressBar

log = __import__('logging').getLogger(__name__)

def make_uuid():
    return unicode(uuid.uuid4())

metadata = MetaData()

class GA_Url(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

url_table = Table('ga_url', metadata,
                      Column('id', types.UnicodeText, primary_key=True,
                             default=make_uuid),
                      Column('period_name', types.UnicodeText),
                      Column('period_complete_day', types.Integer),
                      Column('pageviews', types.UnicodeText),
                      Column('visits', types.UnicodeText),
                      Column('url', types.UnicodeText),
                      Column('department_id', types.UnicodeText),
                      Column('package_id', types.UnicodeText),
                )
mapper(GA_Url, url_table)


class GA_Stat(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

stat_table = Table('ga_stat', metadata,
                  Column('id', types.UnicodeText, primary_key=True,
                         default=make_uuid),
                  Column('period_name', types.UnicodeText),
                  Column('period_complete_day', types.UnicodeText),
                  Column('stat_name', types.UnicodeText),
                  Column('key', types.UnicodeText),
                  Column('value', types.UnicodeText), )
mapper(GA_Stat, stat_table)


class GA_Publisher(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

pub_table = Table('ga_publisher', metadata,
                  Column('id', types.UnicodeText, primary_key=True,
                         default=make_uuid),
                  Column('period_name', types.UnicodeText),
                  Column('publisher_name', types.UnicodeText),
                  Column('views', types.UnicodeText),
                  Column('visits', types.UnicodeText),
                  Column('toplevel', types.Boolean, default=False),
                  Column('subpublishercount', types.Integer, default=0),
                  Column('parent', types.UnicodeText),
)
mapper(GA_Publisher, pub_table)


class GA_ReferralStat(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

referrer_table = Table('ga_referrer', metadata,
                      Column('id', types.UnicodeText, primary_key=True,
                             default=make_uuid),
                      Column('period_name', types.UnicodeText),
                      Column('source', types.UnicodeText),
                      Column('url', types.UnicodeText),
                      Column('count', types.Integer),
                )
mapper(GA_ReferralStat, referrer_table)



def init_tables():
    metadata.create_all(model.meta.engine)


cached_tables = {}


def get_table(name):
    if name not in cached_tables:
        meta = MetaData()
        meta.reflect(bind=model.meta.engine)
        table = meta.tables[name]
        cached_tables[name] = table
    return cached_tables[name]


class Identifier:
    def __init__(self):
        Identifier.dataset_re = re.compile('/dataset/([^/]+)(/.*)?')
        Identifier.publisher_re = re.compile('/publisher/([^/]+)(/.*)?')

    def get_package(self, url):
        # e.g. /dataset/fuel_prices
        # e.g. /dataset/fuel_prices/resource/e63380d4
        dataset_match = Identifier.dataset_re.match(url)
        if dataset_match:
            dataset_ref = dataset_match.groups()[0]
        else:
            dataset_ref = None
        return dataset_ref

    def get_package_and_publisher(self, url):
        # Example urls:
        #       /dataset/fuel_prices
        #       /dataset/d7fc8964-e9da-42ab-8385-cbac70479f4b
        #       /dataset/fuel_prices/resource/e63380d4
        dataset_match = Identifier.dataset_re.match(url)
        if dataset_match:
            dataset_ref = dataset_match.groups()[0]
            dataset = model.Package.get(dataset_ref)
            if dataset:
                if hasattr(dataset, 'owner_org'):
                    # CKAN 2+
                    org = model.Group.get(dataset.owner_org)
                    org_name = org.name if org else None
                else:
                    publisher_groups = dataset.get_groups('organization')
                    org_name = publisher_groups[0].name if publisher_groups else None
                return dataset.name, org_name
            return dataset_ref, None
        else:
            publisher_match = Identifier.publisher_re.match(url)
            if publisher_match:
                return None, publisher_match.groups()[0]
        return None, None

def update_sitewide_stats(period_name, stat_name, data, period_complete_day):
    for k,v in data.iteritems():
        item = model.Session.query(GA_Stat).\
            filter(GA_Stat.period_name==period_name).\
            filter(GA_Stat.key==k).\
            filter(GA_Stat.stat_name==stat_name).first()
        if item:
            item.period_name = period_name
            item.key = k
            item.value = v
            item.period_complete_day = period_complete_day
            model.Session.add(item)
        else:
            # create the row
            values = {'id': make_uuid(),
                     'period_name': period_name,
                     'period_complete_day': period_complete_day,
                     'key': k,
                     'value': v,
                     'stat_name': stat_name
                     }
            model.Session.add(GA_Stat(**values))
        model.Session.commit()


def pre_update_url_stats(period_name):
    q = model.Session.query(GA_Url).\
        filter(GA_Url.period_name==period_name)
    log.debug("Deleting %d '%s' URL records" % (q.count(), period_name))
    q.delete()

    model.Session.flush()
    model.Session.commit()
    model.repo.commit_and_remove()
    log.debug('...done')


def post_update_url_stats():

    """ Check the distinct url field in ga_url and make sure
        it has an All record.  If not then create one.

        After running this then every URL should have an All
        record regardless of whether the URL has an entry for
        the month being currently processed.
    """
    q = model.Session.query(GA_Url).\
        filter_by(period_name='All')
    log.debug("Deleting %d 'All' URL records..." % q.count())
    q.delete()

    # For dataset URLs:
    # Calculate the total views/visits for All months
    log.debug('Calculating Dataset "All" records')
    query = '''select package_id, sum(pageviews::int), sum(visits::int)
               from ga_url
               where package_id != ''
               group by package_id
               order by sum(pageviews::int) desc
               '''
    res = model.Session.execute(query).fetchall()
    # Now get the link between dataset and org as the previous
    # query doesn't return that
    package_to_org = \
        model.Session.query(GA_Url.package_id, GA_Url.department_id)\
             .filter(GA_Url.package_id != None)\
             .group_by(GA_Url.package_id, GA_Url.department_id)\
             .all()
    package_to_org = dict(package_to_org)
    for package_id, views, visits in res:
        values = {'id': make_uuid(),
                  'period_name': "All",
                  'period_complete_day': 0,
                  'url': '',
                  'pageviews': views,
                  'visits': visits,
                  'department_id': package_to_org.get(package_id, ''),
                  'package_id': package_id
                  }
        model.Session.add(GA_Url(**values))

    # For non-dataset URLs:
    # Calculate the total views/visits for All months
    log.debug('Calculating URL "All" records...')
    query = '''select url, sum(pageviews::int), sum(visits::int)
               from ga_url
               where package_id = ''
               group by url
               order by sum(pageviews::int) desc
            '''
    res = model.Session.execute(query).fetchall()

    for url, views, visits in res:
        values = {'id': make_uuid(),
                  'period_name': "All",
                  'period_complete_day': 0,
                  'url': url,
                  'pageviews': views,
                  'visits': visits,
                  'department_id': '',
                  'package_id': ''
                  }
        model.Session.add(GA_Url(**values))
    model.Session.commit()

    log.debug('Done URL "All" records')


def update_url_stats(period_name, period_complete_day, url_data,
                     print_progress=False):
    '''
    Given a list of urls and number of hits for each during a given period,
    stores them in GA_Url under the period and recalculates the totals for
    the 'All' period.
    '''
    progress_total = len(url_data)
    progress_count = 0
    if print_progress:
        progress_bar = GaProgressBar(progress_total)
    urls_in_ga_url_this_period = set(
        result[0] for result in model.Session.query(GA_Url.url)
                                     .filter(GA_Url.period_name==period_name)
                                     .all())
    identifier = Identifier()
    for url, views, visits in url_data:
        progress_count += 1
        if print_progress:
            progress_bar.update(progress_count)

        package, publisher = identifier.get_package_and_publisher(url)

        if url in urls_in_ga_url_this_period:
            item = model.Session.query(GA_Url).\
                filter(GA_Url.period_name==period_name).\
                filter(GA_Url.url==url).first()
            item.pageviews = int(item.pageviews or 0) + int(views or 0)
            item.visits = int(item.visits or 0) + int(visits or 0)
            if not item.package_id:
                item.package_id = package
            if not item.department_id:
                item.department_id = publisher
            model.Session.add(item)
        else:
            values = {'id': make_uuid(),
                      'period_name': period_name,
                      'period_complete_day': period_complete_day,
                      'url': url,
                      'pageviews': views,
                      'visits': visits,
                      'department_id': publisher,
                      'package_id': package
                      }
            model.Session.add(GA_Url(**values))
            urls_in_ga_url_this_period.add(url)
        model.Session.commit()

        if package:
            counts = \
                model.Session.query(func.sum(cast(GA_Url.pageviews,
                                                  types.INTEGER)),
                                    func.sum(cast(GA_Url.visits,
                                                  types.INTEGER))
                                    ) \
                     .filter(GA_Url.period_name!='All') \
                     .filter(GA_Url.url==url) \
                     .all()
            pageviews, visits = counts[0]
            values = {'id': make_uuid(),
                      'period_name': 'All',
                      'period_complete_day': 0,
                      'url': url,
                      'pageviews': pageviews,
                      'visits': visits,
                      'department_id': publisher,
                      'package_id': package
                      }

            model.Session.add(GA_Url(**values))
            model.Session.commit()


def pre_update_sitewide_stats(period_name):
    q = model.Session.query(GA_Stat).\
        filter(GA_Stat.period_name==period_name)
    log.debug("Deleting %d '%s' sitewide records..." % (q.count(), period_name))
    q.delete()

    model.Session.flush()
    model.Session.commit()
    model.repo.commit_and_remove()
    log.debug('...done')


def pre_update_social_stats(period_name):
    q = model.Session.query(GA_ReferralStat).\
        filter(GA_ReferralStat.period_name==period_name)
    log.debug("Deleting %d '%s' social records..." % (q.count(), period_name))
    q.delete()

    model.Session.flush()
    model.Session.commit()
    model.repo.commit_and_remove()
    log.debug('...done')


def update_social(period_name, data):
    for url,data in data.iteritems():
        for entry in data:
            source = entry[0]
            count = entry[1]

            item = model.Session.query(GA_ReferralStat).\
                filter(GA_ReferralStat.period_name==period_name).\
                filter(GA_ReferralStat.source==source).\
                filter(GA_ReferralStat.url==url).first()
            if item:
                item.count = item.count + count
                model.Session.add(item)
            else:
                # create the row
                values = {'id': make_uuid(),
                          'period_name': period_name,
                          'source': source,
                          'url': url,
                          'count': count,
                         }
                model.Session.add(GA_ReferralStat(**values))
            model.Session.commit()


def update_publisher_stats(period_name):
    """
    Updates the publisher stats from the data retrieved for /dataset/*
    and /publisher/*. Will run against each dataset and generates the
    totals for the entire tree beneath each publisher.
    """
    toplevel = get_top_level()
    publishers = model.Session.query(model.Group).\
        filter(model.Group.type=='organization').\
        filter(model.Group.state=='active').all()
    for publisher in publishers:
        views, visits, subpub = update_publisher(period_name, publisher, publisher.name)
        parent, parents = '', publisher.get_parent_groups(type='organization')
        if parents:
            parent = parents[0].name
        item = model.Session.query(GA_Publisher).\
            filter(GA_Publisher.period_name==period_name).\
            filter(GA_Publisher.publisher_name==publisher.name).first()
        if item:
            item.views = views
            item.visits = visits
            item.publisher_name = publisher.name
            item.toplevel = publisher in toplevel
            item.subpublishercount = subpub
            item.parent = parent
            model.Session.add(item)
        else:
            # create the row
            values = {'id': make_uuid(),
                     'period_name': period_name,
                     'publisher_name': publisher.name,
                     'views': views,
                     'visits': visits,
                     'toplevel': publisher in toplevel,
                     'subpublishercount': subpub,
                     'parent': parent
                     }
            model.Session.add(GA_Publisher(**values))
        model.Session.commit()


def update_publisher(period_name, pub, part=''):
    views,visits,subpub = 0, 0, 0
    for publisher in go_down_tree(pub):
        subpub = subpub + 1
        items = model.Session.query(GA_Url).\
                filter(GA_Url.period_name==period_name).\
                filter(GA_Url.department_id==publisher.name).all()
        for item in items:
            views = views + int(item.pageviews)
            visits = visits + int(item.visits)

    return views, visits, (subpub-1)


def get_top_level():
    '''Returns the top level publishers.'''
    return model.Session.query(model.Group).\
           outerjoin(model.Member, model.Member.table_id == model.Group.id and \
                     model.Member.table_name == 'group' and \
                     model.Member.state == 'active').\
           filter(model.Member.id==None).\
           filter(model.Group.type=='organization').\
           order_by(model.Group.name).all()

def get_children(publisher):
    '''Finds child publishers for the given publisher (object). (Not recursive i.e. returns one level)'''
    return publisher.get_children_groups(type='organization')

def go_down_tree(publisher):
    '''Provided with a publisher object, it walks down the hierarchy and yields each publisher,
    including the one you supply.'''
    yield publisher
    for child in get_children(publisher):
        for grandchild in go_down_tree(child):
            yield grandchild

def delete(period_name):
    '''
    Deletes table data for the specified period, or specify 'all'
    for all periods.
    '''
    for object_type in (GA_Url, GA_Stat, GA_Publisher, GA_ReferralStat):
        q = model.Session.query(object_type)
        if period_name != 'All':
            q = q.filter_by(period_name=period_name)
        q.delete()
    model.repo.commit_and_remove()

def get_score_for_dataset(dataset_name):
    '''
    Returns a "current popularity" score for a dataset,
    based on how many views it has had recently.
    '''
    import datetime
    now = datetime.datetime.now()
    last_month = now - datetime.timedelta(days=30)
    period_names = ['%s-%02d' % (last_month.year, last_month.month),
                    '%s-%02d' % (now.year, now.month),
                    ]

    score = 0
    for period_name in period_names:
        score /= 2 # previous periods are discounted by 50%
        entry = model.Session.query(GA_Url)\
                .filter(GA_Url.period_name==period_name)\
                .filter(GA_Url.package_id==dataset_name).first()
        # score
        if entry:
            views = float(entry.pageviews)
            if entry.period_complete_day:
                views_per_day = views / entry.period_complete_day
            else:
                views_per_day = views / 15 # guess
            score += views_per_day

    score = int(score * 100)
    #log.debug('Popularity %s: %s', score, dataset_name)
    return score
