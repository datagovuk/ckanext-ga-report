ckanext-ga-report
=================

**Status:** In current use (data.gov.uk)

**CKAN Version:** 1.7.1+


Overview
--------

For creating detailed reports of CKAN analytics, including totals per group.

Whereas ckanext-googleanalytics focusses on providing page view stats a recent period and for all time (aimed at end users), ckanext-ga-report is more interested in building regular periodic reports (more for site managers to monitor).

Contents of this extension:

 * Use the CLI tool to download Google Analytics data for each time period into this extension's database tables

 * Users can view the data as web page reports


Setup Google Analytics
----------------------

Before you can use this CKAN extension you need to be already collecting Google Analytics data and see it appearing on the Google Analytics website:

1. If your organization already has a Google Analytics "account" then your Google user account needs to be given the "Edit" permission, or you need to work with someone who does have it. OR if your organization doesn't already have a Google Analytics "account", create one.

2. Set up a Google Analytics "property" for your DGU To Go website: https://support.google.com/analytics/answer/1042508?hl=en and note the Tracking ID it gives you. e.g. UA-1010101-1

3. Add the Google Analytics tracking code snippet to your templates by putting it into the ckan.template_footer_end setting in your ckan.ini:

```
ckan.template_footer_end =   <script type="text/javascript">
 <!--//--><![CDATA[//><!--
 (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
 (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
 m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
 })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
 ga('create', 'UA-1010101-1', 'auto');
 ga('send', 'pageview');
 //--><!]]>
 </script>
```

  Notes:

  * There is a space at the start of every line apart from the first. This is required for the config file format, to attach multiple lined values to an option.

  * If copying into your config, remember to adjust the Tracking ID to be your own one.

  * This particular snippet is the one for the 'Universal Analytics' version of Google Analytics, and changes with different versions. If you are unsure, find the tracking code that you need using the Google Analytics web interface: https://support.google.com/analytics/answer/1008080?hl=en BUT remember to add the spaces at the start of each line when you paste it into your config file.

4. Deploy to your website, check the tracking code snippet is appearing in your page source and click on a few pages to create some initial traffic. You'll have to wait up to 24 hours to see the traffic appearing in the Google Analytics web pages.


Installation
------------

1. Activate you CKAN python environment and install this extension's software:
```
$ pyenv/bin/activate
$ pip install -e  git+https://github.com/datagovuk/ckanext-ga-report.git#egg=ckanext-ga-report
```

2. Install dependencies (e.g. Google's python client library):
```
$ pip install -r ckanext-ga-report/requirements.txt
```

3. Ensure you development.ini (or similar) contains the info about your Google Analytics account and configuration:

```
googleanalytics.id = UA-1010101-1
googleanalytics.account = Account name (e.g. data.gov.uk, see top level item at https://www.google.com/analytics)
googleanalytics.token.filepath = ~/pyenv/token.dat
ga-report.period = monthly
ga-report.bounce_url = /
```

   The ga-report.bounce_url specifies a particular path to record the bounce rate for. Typically it is / (the home page).

4. Set up this extension's database tables using a paster command. (Ensure your CKAN pyenv is still activated, run the command from ``src/ckanext-ga-report``, alter the ``--config`` option to point to your site config file):
```
$ paster initdb --config=../ckan/development.ini
```

5. Enable the extension in your CKAN config file by adding it to ``ckan.plugins``:
```
ckan.plugins = ga-report
```

Problem shooting
----------------

* `(ProgrammingError) relation "ga_url" does not exist`
  This means that the ``paster initdb`` step has not been run successfully. Refer to the installation instructions for this extension.


Authorization
--------------

Before you can access the data, you need to create an OAUTH token of type "Installed application", which you can do by following the [instructions](https://developers.google.com/analytics/resources/tutorials/hello-analytics-api) the outcome of which will be a file called credentials.json (also known as client_secrets.json) which should look like credentials.json.template only with the relevant fields completed. The steps are listed below for convenience.

1. Visit the [Google APIs Console](https://code.google.com/apis/console) using a Google account that has access to the Google Analytics for your project. (That Google user has a quota of API requests and has the power to revoke API access via the token associated.) You may have to accept the Terms of Service at this point.

2. Create a project or use an existing project.

3. In the [Services pane](https://code.google.com/apis/console#:services), activate "Analytics API" for your project.

4. Go to the [API Access pane](https://code.google.com/apis/console/#:access)

5. Click "Create new Client ID"

6. Select type "Installed application" (in this context, 'ckanext-ga-report' is the application)

7. Now shown the "Consent screen", you only need to provide the Product Name (ckanext-ga-report although it is not important).

8. In the "Create Client ID" dialog again you need to select "Installed application" and type "Other"

9. It will now show the information that go into credentials.json: Client ID, Client secret, and Redirect URIs. You can click "Download JSON" to save it. Now rename the file to credentials.json.

10. This paster command should be run on any machine with ckanext-ga-report installed and the credentials.json file at hand:

        $ paster --plugin=ckanext-ga-report getauthtoken credentials.json --config=../ckan/development.ini

    This will try to start a web browser at a URL like this:

        https://accounts.google.com/o/oauth2/auth?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fanalytics.readonly&redirect_uri=http%3A%2F%2Flocalhost%3A8080%2F&response_type=code&client_id=769797987376-tj82tp3ttp5guhiioyi6jneecd7mj5g.apps.googleusercontent.com&access_type=offline

    If you are running it on a server or VM without a browser then you can simply copy & paste that URL into a local web browser.

11. The web page asks you to log-in to Google - use the same account you created the credentials with earlier.

12. In the browser it now asks "ckanext-ga-report would like to view your Google Analytics data". Click "Accept".

13. Your browser will now be redirected to something like:

        http://localhost:8080/?code=4/Com0kAHaio858diw2dv70u3rhjwkjsduofyzj0.g8f93jd889sjsj29d-If93

    If you are in a browser that is not on the same machine as the paster command than you will see a browser error. In this case you need to resolve that URL on the machine where the paster command is running (but in a new terminal):

        curl http://localhost:8080/?code=4/Com0kAHaio858diw2dv70u3rhjwkjsduofyzj0.g8f93jd889sjsj29d-If93

    The paster window should now say "Authentication successful" and the token.dat file will be created.

14. Now ensure you reference the correct path to your token.dat in your CKAN config file (e.g. development.ini)::

    googleanalytics.token.filepath = ~/pyenv/token.dat


Tutorial
--------

Download some GA data and store it in CKAN's database. (Ensure your CKAN pyenv is still activated, run the command from `src/ckanext-ga-report`, alter the `--config` option to point to your site config file) and specifying the name of your auth file (token.dat by default) from the previous step:

    $ paster loadanalytics latest --config=../ckan/development.ini

The value after the token file is how much data you want to retrieve, this can be

* **all**         - data for all time (since 2010)

* **latest**      - (default) just the 'latest' data

* **YYYY-MM-DD**  - just data for all time periods going back to (and including) this date



Software Licence
================

This software is developed by Cabinet Office. It is Crown Copyright and opened up under dual licences:

1. Open Government Licence (OGL) (which is compatible with Creative Commons Attibution License). OGL terms: http://www.nationalarchives.gov.uk/doc/open-government-licence/

2. GNU Affero General Public License (AGPL-3.0). Terms: http://opensource.org/licenses/AGPL-3.0
