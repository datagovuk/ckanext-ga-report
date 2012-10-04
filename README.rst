ckanext-ga-report
=================

**Status:** Development

**CKAN Version:** 1.7.1+


Overview
--------

For creating detailed reports of CKAN analytics, including totals per group.

Whereas ckanext-googleanalytics focusses on providing page view stats a recent period and for all time (aimed at end users), ckanext-ga-report is more interested in building regular periodic reports (more for site managers to monitor).

Contents of this extension:

 * Use the CLI tool to download Google Analytics data for each time period into this extension's database tables

 * Users can view the data as web page reports


Installation
------------

1. Activate you CKAN python environment and install this extension's software::

    $ pyenv/bin/activate
    $ pip install -e  git+https://github.com/okfn/ckanext-ga-report.git#egg=ckanext-ga-report

2. Ensure you development.ini (or similar) contains the info about your Google Analytics account and configuration::

      googleanalytics.id = UA-1010101-1
      googleanalytics.username = googleaccount@gmail.com
      googleanalytics.password = googlepassword
      ga-report.period = monthly

   Note that your password will be readable by system administrators on your server. Rather than use sensitive account details, it is suggested you give access to the GA account to a new Google account that you create just for this purpose.

3. Set up this extension's database tables using a paster command. (Ensure your CKAN pyenv is still activated, run the command from ``src/ckanext-ga-report``, alter the ``--config`` option to point to your site config file)::

    $ paster initdb --config=../ckan/development.ini

4. Enable the extension in your CKAN config file by adding it to ``ckan.plugins``::

    ckan.plugins = ga-report


Tutorial
--------

Download some GA data and store it in CKAN's db. (Ensure your CKAN pyenv is still activated, run the command from ``src/ckanext-ga-report``, alter the ``--config`` option to point to your site config file)::

    $ paster loadanalytics latest --config=../ckan/development.ini


Software Licence
================

This software is developed by Cabinet Office. It is Crown Copyright and opened up under the Open Government Licence (OGL) (which is compatible with Creative Commons Attibution License).

OGL terms: http://www.nationalarchives.gov.uk/doc/open-government-licence/
