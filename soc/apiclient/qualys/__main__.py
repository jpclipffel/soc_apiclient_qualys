import os
import argparse
import logging
import logging.handlers
import time
from tabulate import tabulate
import re
import json
from pkg_resources import resource_filename as pkgrs
from . import QualysAPI, tools, autoreport


def command_list_scans(args):
    logger = logging.getLogger("soc.apiclient.qualys.__main__.command_list_scans")
    qualys = QualysAPI(args.config)
    table = []
    for i in qualys.scans:
        if re.match(args.filter, str(i.title)):
            table.append([i.title, i.ref, i.status, time.strftime("%d/%m/%y %H:%M:%S", i.launch)])
    return table, ["Title", "Reference", "Status", "Time (%d/%m/%y %H:%M:%S)"]


def command_list_reports(args):
    logger = logging.getLogger("soc.apiclient.qualys.__main__.command_list_reports")
    qualys = QualysAPI(args.config)
    table = []
    for i in qualys.reports:
        if re.match(args.filter, str(i.title)):
            table.append([i.title, i.id, i.state, i.output_format, time.strftime("%d/%m/%y %H:%M:%S", i.launch), time.strftime("%d/%m/%y %H:%M:%S", i.expiration)])
    return table, ["Title", "ID", "State", "Format", "Launch", "Expiration"]


def command_list_templates(args):
    logger = logging.getLogger("soc.apiclient.qualys.__main__.command_list_templates")
    qualys = QualysAPI(args.config)
    table = []
    for i in qualys.templates:
        if re.match(args.filter, str(i.title)):
            table.append([i.title, i.id, i.template_type])
    return table, ["Title", "ID", "Type"]


def command_list(args):
    logger = logging.getLogger("soc.apiclient.qualys.__main__.command_list")
    if args.object == "scans":
        table, headers = command_list_scans(args)
    elif args.object == "reports":
        table, headers = command_list_reports(args)
    elif args.object == "templates":
        table, headers = command_list_templates(args)
    print(tabulate(table, headers=headers))


def command_generate(args):
    logger = logging.getLogger("soc.apiclient.qualys.__main__.command_generate")
    qualys = QualysAPI(args.config)
    template = qualys.find_templates(templates_title=args.template)[0]
    scans = qualys.find_scans(scans_title=args.scans)
    report = qualys.generate_report(args.name, template, scans, args.format)
    print("Report id {} is running".format(report.id))


def command_download(args):
    logger = logging.getLogger("soc.apiclient.qualys.__main__.")
    qualys = QualysAPI(args.config)
    report = qualys.find_reports(reports_title=args.name)[0]
    report_data = qualys.fetch_report(report)
    tools.save_report(report_data, report, args.filename, args.directory)


def command_autoreport(args):
    logger = logging.getLogger("soc.apiclient.qualys.__main__.command_autoreport")
    # Errors and warnings
    errors = []
    warnings = []
    reports = []
    # Configuration.
    qualys = QualysAPI(args.config)
    manager = autoreport.ProfileManager(args.profiles)
    # Select requested profiles.
    if args.profile == "__all__":
        requested_profiles = [p for p in manager.profiles]
    else:
        requested_profiles = [args.profile, ]
    # Run profiles.
    for profile_name in requested_profiles:
        profile = manager.profile(profile_name)
        # Run profile's reports.
        try:
            for r in profile.reports:
                # Find profile's scans and template.
                scans = qualys.find_scans(scans_title=r["scans"])
                template = qualys.find_templates(templates_title=r["template"])[0]
                # Cleanup duplicates scans.
                scans = tools.filter_duplicate_scans(scans)
                # Health check the scans.
                warnings = warnings + tools.healtcheck_scans(scans=scans, profile=profile)
                # Generate report.
                report = qualys.generate_report(
                    title=r["name"],
                    template=template,
                    scans=scans,
                    output_format=r["format"],
                    max_failures=profile.limits["generate_report"]["max_failures"],
                    wait_failures=profile.limits["generate_report"]["wait_failures"])
                while report.state == "Running":
                    report = qualys.find_reports(reports_id=report.id)[0]
                    time.sleep(5)
                # Setup report filename.
                report_name = report.title if report.title is not None or len(str(report.title)) > 0 else report.id
                filename = "{} - {}.{}".format(report_name, time.strftime(profile.timeformat, report.launch), report.output_format)
                # Fetch report.
                report_data = qualys.fetch_report(report)
                # Save report.
                tools.save_report(report_data, report, filename=filename, directory=profile.directory)
                reports.append({"filename": filename, "directory": profile.directory, "report": report, "profile": profile})
        except Exception as err:
            print("exception: {}".format(str(err)))
            logger.exception(err)
            errors.append("autoreport general error: exception: {}".format(str(err)))
        # Mail notifiction.
        tools.notify_mail(profile.mail_subject,
                          profile.mail_template,
                          variables={"errors": errors, "warnings": warnings, "reports": reports, "profile": args.profile},
                          recipients=profile.mail_recipients,
                          cc=profile.mail_cc,
                          sender=profile.mail_sender,
                          server=profile.mail_server)


def main():
    # Arguments parser.
    parser = argparse.ArgumentParser(description="SOC client API for Qualys")
    # Globals arguments.
    parser.add_argument("--config", type=str, default=pkgrs(__name__, "static/qcrc.ini"), help="Qualys API configuration file")
    parser.add_argument("--logfile", type=str, default=None)
    # Commands sub-parsers.
    sp = parser.add_subparsers(dest="command", help="Command")
    sp.required = True
    # 'list' command.
    p_list = sp.add_parser("list", help="List all instances of a given object")
    p_list.set_defaults(func=command_list)
    p_list.add_argument("object", choices=["scans", "reports", "templates"], help="Objects type")
    p_list.add_argument("--filter", type=str, default=".*", help="Filter on regex")
    # 'generate' command.
    p_report = sp.add_parser("generate", help="Generate the requested report")
    p_report.set_defaults(func=command_generate)
    p_report.add_argument("--name", type=str, required=True, help="Report name")
    p_report.add_argument("--template", type=str, required=True, help="Template's title")
    p_report.add_argument("--scans",  nargs='+', required=True, help="Scan(s) name(s)")
    p_report.add_argument("--format", type=str, choices=["pdf", "csv"], default="pdf", help="Report format")
    # 'download' command.
    p_download = sp.add_parser("download", help="Download the requested report")
    p_download.set_defaults(func=command_download)
    p_download.add_argument("--name", type=str, required=True, help="Report name")
    p_download.add_argument("--directory", type=str, default=None, help="Download directory (defaults to current directory)")
    p_download.add_argument("--filename", type=str, default=None, help="Download filename (defaults to report name)")
    # 'autoreport' command.
    p_autoreport = sp.add_parser("autoreport", help="Automatically generate reports, download them and notify by mail")
    p_autoreport.set_defaults(func=command_autoreport)
    p_autoreport.add_argument("--profiles", type=str, default=pkgrs(__name__, "static/profiles.json"), help="Profiles configuration file")
    p_autoreport.add_argument("profile", type=str, help="Profile name")
    # Parse arguments.
    args = parser.parse_args()
    # Logging.
    logger = logging.getLogger("soc.apiclient.qualys")
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    if args.logfile is not None:
        logger.addHandler(logging.handlers.RotatingFileHandler(args.logfile, mode='a', maxBytes=1000000, backupCount=0))
    # Set log format on all handlers.
    logformatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    for handler in logger.handlers:
        handler.setFormatter(logformatter)
    # Execution.
    try:
        args.func(args)
    except Exception as error:
        print("Error: {err}".format(err=str(error)))
        logger.exception(error)
        raise


if __name__ == "__main__":
    main()
