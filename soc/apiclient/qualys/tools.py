import os
import json
import jsonschema
import smtplib
import getpass
import socket
import jinja2
import jinja2.meta
import logging
import collections
import time
import pprint
from datetime import datetime
from pkg_resources import resource_filename as pkgrs
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def save_report(data, report, filename=None, directory=None):
    """Saves a report file locally.

    Arguments:
        data (str or bytes): File data.
        report (QualysAPI.Report): Report object instance.
        filename (str): File name.
        directory (str, optional): Directory name.
    """
    # Resolve filename.
    if filename is None:
        if report.title is None or len(report.title) < 1:
            filename = "{}.{}".format(str(report.id), report.output_format)
        else:
            filename = "{}.{}".format(report.title, report.output_format)
    # Resolve directory.
    if directory is None:
        directory = os.getcwd()
    # Create directory if needed.
    if not os.path.isdir(directory):
        os.makedirs(directory)
    # Save report.
    with open(os.path.join(os.path.abspath(directory), filename), 'wb') as fd:
        fd.write(data.encode("utf-8"))


def notify_mail(subject, template, variables={}, recipients=[], cc=[], sender="", server="127.0.0.1", port=25):
    """Sends a notification mail.

    Arguments:
        subject (str): E-mail subject.
        template (str): Path too e-mail body template (HTML source).
        variables (dict, optional): E-mail template variables.
        recipients (list of str, optional): E-mail recipients.
        cc (list of str, optional): E-mail CC recipients.
        sender (str, optional): E-mail sender address.
        server (str, optional): E-mail gateway host.
        port (int, optional): E-mail gateway port.
    """
    logger = logging.getLogger("soc.apiclient.qualys.tools.notify_mail")
    # Common setup.
    # Create mail and setup object.
    email = MIMEMultipart()
    email["Subject"] = subject
    email["from"] = sender
    email["To"] = ", ".join(recipients)
    email["CC"] = ", ".join(cc)
    # Setup mail body.
    with open(template, 'r') as fd:
        logger.info("reading mail template (template: {})".format(template))
        payload = fd.read()
    # Log the mail template variables.
    logger.info("mail template variables: {}".format(pprint.pprint(variables)))
    # Validate mail template variables.
    logger.info("validating mail template against provided variables")
    env = jinja2.Environment()
    ast = env.parse(payload)
    missing = [v for v in jinja2.meta.find_undeclared_variables(ast) if v not in variables]
    if len(missing) > 0:
        raise Exception("missing variables {vars}".format(vars=", ".join(missing)))
    # Render and attach mail template.
    logger.info("rendering mail template")
    tpl = jinja2.Template(payload)
    payload = tpl.render(**variables)
    email.attach(MIMEText(payload, "html"))
    # Send mail.
    logger.info("sending mail (from: {}, to: {}, subject: {}, host={}, port={})".format(sender, email["To"], email["Subject"], server, port))
    if len(recipients) > 0:
        smtp_client = smtplib.SMTP(host=server, port=port)
        errors = smtp_client.sendmail(sender, recipients + cc, email.as_string())
        if len(errors) > 0:
            print(errors)
            raise Exception("cannot send mail")
        smtp_client.quit()
    else:
        logger.warning("mail not sent: no recipients")



def filter_duplicate_scans(scans):
    """Detects and remove duplicates scans by keeping only the most recent.

    Arguments:
        scans (list of Scans): The list of scans to check.

    Returns:
        list: List of scans.
    """
    logger = logging.getLogger("soc.apiclient.qualys.tools.filter_duplicate_scans")
    results = []
    # Create a named list of scans.
    scandb = {}
    for scan in scans:
        if scan.title not in scandb:
            scandb[scan.title] = [scan, ]
        else:
            scandb[scan.title].append(scan)
    # Re-order the scans.
    logger.info("cleaning-up the scans list")
    for scan_name, scans_list in scandb.items():
        if len(scans_list) > 1:
            logger.info("multiple versions for scan '{}': {} occurences".format(scan_name, len(scans_list)))
            #results.append(sorted(scans_list, reverse=False)[0])
            scans_list.sort(key=lambda scan: time.mktime(scan.launch))
            results.append(scans_list[-1])
            logger.info("kept scan '{scan_name}' date '{scan_date}' (all dates: {all_dates})".format(
                scan_name=scan_name,
                scan_date=time.strftime("%d/%m/%y %H:%M:%S", results[-1].launch),
                all_dates=",".join([time.strftime("%d/%m/%y %H:%M:%S", s.launch) for s in scans_list])))
        else:
            results.append(scans_list[0])
            logger.info("kept scan '{}' date '{}' (no other date)".format(scan_name, time.strftime("%d/%m/%y %H:%M:%S", results[-1].launch)))
    return results


def check_schedule(profile):
    """Check if a profile must be run.

    Compare thee last run time of profile's report to current time.
    If the delta is >= to the profile's autoreport schedule, returns True.
    False otherwise.

    Arguments:
        profile (object): profile specifying the autoreport schedule.
    """
    logger = logging.getLogger("soc.apiclient.qualys.tools.healtcheck_scans")
    # Fetch the creation timestamp of each report in the profile.


def healtcheck_scans(scans, profile):
    """Check the scans healthness.

    Arguments:
        scans (list of Scans): The list of scans to check.
        profile (object): profile specifying the healtcheck values.

    Returns:
        list: List of warnings.
    """
    logger = logging.getLogger("soc.apiclient.qualys.tools.healtcheck_scans")

    def duplicate_titles():
        logger.info("looking for duplicate titles")
        counted = ["{} ({} occurences)".format(title, count) for title, count in dict(collections.Counter([s.title for s in scans])).items() if count > 1]
        if len(counted) > 0:
            msg = "duplicate scans reference: {}".format(", ".join(counted))
            logger.warning(msg)
            return [msg, ]
        return []

    def timestamp_distance():
        logger.info("looking for suspicous launch time distance")
        results = []
        for ref_scan in scans:
            for scan in scans:
                # Cast time struct in datetime
                ref_scan_dt = datetime.fromtimestamp(time.mktime(ref_scan.launch))
                scan_dt = datetime.fromtimestamp(time.mktime(scan.launch))
                # Calculate time delta
                distance = (ref_scan_dt - scan_dt).total_seconds()
                # Check delta
                if distance > profile.healtcheck_timediff_seconds:
                    msg = "time delta too high between {} ({}) and {} ({}) ({} seconds, tolerance is {})".format(
                        ref_scan.title,ref_scan.ref,
                        scan.title, scan.ref,
                        distance, profile.healtcheck_timediff_seconds
                    )
                    logger.warning(msg)
                    results.append(msg)
        return results

    def scan_status():
        logger.info("looking for unfinished scans")
        results = []
        for scan in scans:
            if scan.status != "Finished":
                results.append("Unfinished scan: {} (ref: {}, status: {})".format(scan.title, scan.ref, scan.status))
        return results

    return duplicate_titles() + timestamp_distance() + scan_status()
