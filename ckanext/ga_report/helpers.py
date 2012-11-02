import logging
import operator
import ckan.lib.base as base
import ckan.model as model

from ckanext.ga_report.ga_model import GA_Url, GA_Publisher
from ckanext.ga_report.controller import _get_publishers
_log = logging.getLogger(__name__)

def popular_datasets(count=10):
    import random

    publisher = None
    publishers = _get_publishers(30)
    total = len(publishers)
    while not publisher or not datasets:
        rand = random.randrange(0, total)
        publisher = publishers[rand][0]
        if not publisher.state == 'active':
            publisher = None
            continue
        datasets = _datasets_for_publisher(publisher, 10)[:count]

    ctx = {
        'datasets': datasets,
        'publisher': publisher
    }
    return base.render_snippet('ga_report/ga_popular_datasets.html', **ctx)

def single_popular_dataset(top=20):
    import random

    datasets = {}
    rand = random.randrange(0, top)
    entry = model.Session.query(GA_Url).\
        filter(GA_Url.url.like('/dataset/%')).\
        order_by('ga_url.pageviews::int desc')[rand]


    dataset = None
    while not dataset:
        dataset = model.Package.get(entry.url[len('/dataset/'):])
        if dataset and not dataset.state == 'active':
            dataset = None
        else:
            publisher = model.Group.get(entry.department_id)

    ctx = {
        'dataset': dataset,
        'publisher': publisher
    }
    return base.render_snippet('ga_report/ga_popular_single.html', **ctx)


def most_popular_datasets(publisher, count=20):

    if not publisher:
        _log.error("No valid publisher passed to 'most_popular_datasets'")
        return ""

    results = _datasets_for_publisher(publisher, count)

    ctx = {
        'dataset_count': len(datasets),
        'datasets': results,

        'publisher': publisher
    }

    return base.render_snippet('ga_report/publisher/popular.html', **ctx)

def _datasets_for_publisher(publisher, count):
    datasets = {}
    entries = model.Session.query(GA_Url).\
        filter(GA_Url.department_id==publisher.name).\
        filter(GA_Url.url.like('/dataset/%')).\
        order_by('ga_url.pageviews::int desc').all()
    for entry in entries:
        if len(datasets) < count:
            p = model.Package.get(entry.url[len('/dataset/'):])
            if not p in datasets:
                datasets[p] = {'views':0, 'visits': 0}
            datasets[p]['views'] = datasets[p]['views'] + int(entry.pageviews)
            datasets[p]['visits'] = datasets[p]['visits'] + int(entry.visitors)

    results = []
    for k, v in datasets.iteritems():
        results.append((k,v['views'],v['visits']))

    return sorted(results, key=operator.itemgetter(1), reverse=True)
