import os
import qualysapi
import lxml.objectify
import requests
import time
import logging
import urllib3


urllib3.disable_warnings()


def iso_to_ts(iso):
    return time.strptime(str(iso).replace('Z', "GMT"), "%Y-%m-%dT%H:%M:%S%Z")


class Scan:
    def __init__(self, details):
        self.logger = logging.getLogger("soc.apiclient.qualys.Scan")
        self.logger.debug("building Scan object instance")
        # ---
        self.duration = details.DURATION
        self.launch = iso_to_ts(details.LAUNCH_DATETIME)
        self.processed = details.PROCESSED
        self.priority = details.PROCESSING_PRIORITY
        self.ref = details.REF
        self.status = details.STATUS.STATE
        self.target = details.TARGET
        self.title = details.TITLE
        self.type = details.TYPE
        self.user = details.USER_LOGIN


class Template:
    def __init__(self, details):
        self.logger = logging.getLogger("soc.apiclient.qualys.Template")
        self.logger.debug("building Template object instance")
        # ---
        self.is_global = details.GLOBAL
        self.id = int(details.ID)
        self.last_update = details.LAST_UPDATE
        self.template_type = details.TEMPLATE_TYPE
        self.title = getattr(details, "TITLE", None)
        self.type = details.TYPE
        self.user_lastname = details.USER.LASTNAME
        self.user_firstname = details.USER.FIRSTNAME
        self.user_login = details.USER.LOGIN


class Report:
    def __init__(self, details):
        self.logger = logging.getLogger("soc.apiclient.qualys.Report")
        self.logger.debug("building Report object instance")
        # ---
        self.expiration = iso_to_ts(details.EXPIRATION_DATETIME)
        self.id = int(details.ID)
        self.launch = iso_to_ts(details.LAUNCH_DATETIME)
        self.output_format = details.OUTPUT_FORMAT
        self.size = details.SIZE
        self.state = details.STATUS.STATE
        self.title = getattr(details, "TITLE", None)
        self.type = details.TYPE
        self.user = details.USER_LOGIN


class QualysAPI:
    def __init__(self, config_path):
        """Initializes the object instance.

        Arguments:
            config_path (str): Path to the Qualys API configuration file.
        """
        self.logger = logging.getLogger("soc.apiclient.qualys.QualysAPI")
        self.logger.info("connecting to Qualys API server")
        self.qgc = qualysapi.connect(config_path)

    @property
    def scans(self):
        """Returns the scans' list.
        """
        api_url = "/api/2.0/fo/scan/"
        api_arg = {"action": "list"}
        scans = []
        self.logger.info("retrieving scans list (api_url: {})".format(api_url))
        for scan in lxml.objectify.fromstring(self.qgc.request(api_url, api_arg).encode("utf-8")).RESPONSE.SCAN_LIST.SCAN:
            scans.append(Scan(scan))
        return scans

    @property
    def templates(self):
        """Returns the templates' list.
        """
        api_url = "https://{}/msp/report_template_list.php".format(self.qgc.server)
        templates = []
        self.logger.info("retrieving templates list (api_url: {})".format(api_url))
        for template in lxml.objectify.fromstring(requests.get(api_url, auth=self.qgc.auth).content).REPORT_TEMPLATE:
            templates.append(Template(template))
        return templates

    @property
    def reports(self):
        """Returns the reports' list.
        """
        api_url = "/api/2.0/fo/report/"
        api_arg = {"action": "list"}
        reports = []
        self.logger.info("retrieving reports list (api_url: {})".format(api_url))
        for report in lxml.objectify.fromstring(str(self.qgc.request(api_url, api_arg))).RESPONSE.REPORT_LIST.REPORT:
            reports.append(Report(report))
        return reports

    def find_object(self, stack, needle, values):
        found   = [obj for obj in stack if getattr(obj, needle) in values]
        missing = [val for val in values if val not in [getattr(obj, needle) for obj in found]]
        return (found, missing)

    def find_reports(self, reports_id=None, reports_title=None):
        """Finds reports by ID.

        Arguments:
            reports_id (int or list of int): Report(s) ID.
            reports_title (str or list of str): Report(s) title.

        Returns:
            list: List of Report instances.
        """
        stack = self.reports
        needle = reports_id is not None and "id" or "title"
        values_raw = reports_id is not None and reports_id or reports_title
        values = not isinstance(values_raw, list) and [values_raw, ] or values_raw
        self.logger.info("searching reports: {}".format(", ".join([str(v) for v in values])))
        found, missing = self.find_object(stack=stack, needle=needle, values=values)
        if len(missing) > 0:
            raise Exception("no such reports: {}".format(", ".join([str(i) for i in missing])))
        return found
        # reports_id = isinstance(reports_id, int) and [reports_id, ] or reports_id
        # self.logger.info("searching for reports ID {}".format(", ".join(reports_id)))
        # found_reports = [r for r in self.reports if r.id in reports_id]
        # missing = [r for r in reports_id if r not in [r.id for r in found_reports]]
        # if len(missing) > 0:
        #     raise Exception("no such reports: {}".format(", ".format(missing)))
        # return found_reports

    def find_templates(self, templates_title):
        """Finds templates by title.

        Arguments:
            templates_title (str or list of str): Template(s) title.

        Returns:
            list: List of Template instances.
        """
        values = not isinstance(templates_title, list) and [templates_title, ] or templates_title
        self.logger.info("searching templates: {}".format(", ".join(values)))
        found, missing = self.find_object(stack=self.templates, needle="title", values=values)
        if len(missing) > 0:
            raise Exception("no such templates: {}".format(", ".join([str(i) for i in missing])))
        return found
        # templates_title = isinstance(templates_title, str) and [templates_title, ] or templates_title
        # self.logger.info("searching for templates title {}".format(", ".join(templates_title)))
        # found_templates = [t for t in self.templates if t.title in templates_title]
        # missing = [t for t in templates_title if t not in [t.title for t in found_templates]]
        # if len(missing) > 0:
        #     raise Exception("no such templates: {}".format(", ".format(missing)))
        # return found_templates

    def find_scans(self, scans_title):
        """Finds scans by title.

        Arguments:
            scans_title (str or list of str): Scan(s) title.

        Returns:
            list: List of Scan instances.
        """
        values = not isinstance(scans_title, list) and [scans_title, ] or scans_title
        self.logger.info("searching scans: {}".format(", ".join(values)))
        found, missing = self.find_object(stack=self.scans, needle="title", values=values)
        if len(missing) > 0:
            print(missing)
            raise Exception("no such scans: {}".format(", ".join([str(i) for i in missing])))
        return found
        # scans_title = isinstance(scans_title, str) and [scans_title, ] or scans_title
        # self.logger.info("searching for scans title {}".format(", ".join(scans_title)))
        # found_scans = [t for t in self.templates if t.title in scans_title]
        # missing = [s for s in scans_title if s not in [s.title for s in found_scans]]
        # if len(missing) > 0:
        #     raise Exception("no such scans: {}".format(", ".format(missing)))
        # return found_scans

    def generate_report(self, title, template, scans, output_format="pdf", max_failures=0, wait_failures=5):
        """Generates the requested `report`.

        Arguments:
            title (str): The file name of the report which will be generated.
            template (Template): A QualysAPI's `Template` object instance.
            scans (list of Scan): List of QualysAPI's `Scan` object instance.
            output_format (str, optional): Report output format (defaults to 'pdf').
            max_failures (int, optional): Tolerates maximum `max_failures` while waiting for report to be placed in queue.
            wait_failures (int, optional): Wait `wait_failures` seconds between each failure.

        Returns:
            A Report object instance.
        """
        api_url = "/api/2.0/fo/report/"
        api_arg = {"action": "launch",
                   "template_id": template.id,
                   "report_title": title,
                   "output_format": output_format,
                   "report_type": "Scan",
                   "report_refs": ",".join([str(scan.ref) for scan in scans])}
        self.logger.info("generating report (name: '{}', template: '{}', scans: '{}', output_format: '{}', api_url: {})".format(
            title,
            template.title,
            api_arg["report_refs"],
            output_format,
            api_url))
        try:
            response = self.qgc.request(api_url, api_arg).encode("utf-8")
            report_id = int(lxml.objectify.fromstring(response).RESPONSE.ITEM_LIST.ITEM.VALUE)
            self.logger.info("report generation in progress (report_id: {})".format(report_id))
            time.sleep(5)
            failed = 0
            while True:
                try:
                    return self.find_reports(reports_id=report_id)[0]
                except Exception as err:
                    failed += 1
                    self.logger.warning("failed to find report: max_failures={}, failed={}, reason=\"{}\"".format(max_failures, failed, str(err)))
                    if failed >= max_failures:
                        raise err
                    else:
                        time.sleep(wait_failures)
        except Exception as error:
            self.logger.exception(error)
            raise error

    def fetch_report(self, report):
        """Fetch a report file.

        Arguments:
            report (Report): A QualysAPI's `Report` object instance.
        """
        api_url = "/api/2.0/fo/report/"
        api_arg = {"action": "fetch", "id": report.id}
        self.logger.info("fetching report ID {} (api_url: {})".format(report.id, api_url))
        return self.qgc.request(api_url, api_arg)
