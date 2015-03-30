import collections
from itertools import groupby

from sqlalchemy import func

from ckan import model
from ckan.lib.helpers import OrderedDict
from ckanext.dgu.lib.publisher import go_up_tree
from ga_model import GA_Url  # , GA_Stat, GA_ReferralStat, GA_Publisher


def publisher_report(metric='views'):
    q = '''
        select department_id, period_name, %s metric
        from ga_url
        where department_id <> ''
          and package_id <> ''
        group by department_id, period_name
        order by department_id
    '''
    orgs = dict(model.Session.query(model.Group.name, model.Group).all())

    if metric == 'views':
        sqla_function = func.sum(GA_Url.pageviews)
        sql_function = 'sum(pageviews::int)'
    elif metric == 'visits':
        sqla_function = func.sum(GA_Url.visits)
        sql_function = 'sum(visits::int)'
    elif metric == 'downloads':
        sqla_function = func.sum(GA_Url.downloads)
    elif metric == 'viewsdownloads':
        sqla_function = func.sum(GA_Url.downloads)

    org_period_count = model.Session.connection().execute(q % sql_function)

    org_counts = collections.defaultdict(dict)
    for org_name, period_name, count in org_period_count:
        org_counts[org_name][period_name] = count

    org_counts = sorted(org_counts.items(),
                        key=lambda x: -x[1].get('All', 0))

    all_periods = [
        res[0] for res in model.Session.query(GA_Url.period_name)
                               .group_by(GA_Url.period_name)
                               .order_by(GA_Url.period_name)
                               .all()]
    rows = []
    for org_name, counts in org_counts:
        org = orgs.get(org_name)
        if not org:
            continue
        top_org = list(go_up_tree(org))[-1]

        row = OrderedDict((
            ('organization title', org.title),
            ('organization name', org.name),
            ('top-level organization title', top_org.title),
            ('top-level organization name', top_org.name),
            ))
        for period_name in all_periods:
            row[period_name] = counts.get(period_name, 0)
        rows.append(row)

    # Group the periods by year, to help the template draw the table nicely
    #all_periods_tuples = [period.split('-') for period in all_periods
    #                      if '-' in period]
    #all_periods_tuples.sort(key=lambda x: x[0])
    #all_periods_by_year = [
    #    (year, [p for y, p in year_periods])
    #    for year, year_periods in groupby(all_periods_tuples, lambda x: x[0])]

    return {'table': rows,
            'all periods': all_periods,
            #'all periods by year': all_periods_by_year
            }


publisher_report_info = {
    'name': 'site-usage-publisher',
    'title': 'Site usage by publisher',
    'description': 'Usage statistics, by publisher for each month. Data is from Google Analytics.',
    'option_defaults': None,
    'option_combinations': None,
    'generate': publisher_report,
    'template': 'report/publisher.html',
    }
