import logging
import json
import jsonschema
from pkg_resources import resource_filename as pkgrs


schema_mail = {
    "properties": {
        "template": {
            "type": ["string", "null"]
        },
        "subject": {
            "type": "string"
        },
        "recipients": {
            "type": "array", 
            "items": {
                "type": "string"
            }
        },
        "cc": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "sender": {
            "type": "string"
        },
        "server": {
            "type": "string"
        }
    }
}

schema_healthcheck = {
    "properties": {
        "timediff_seconds": {
            "type": "integer"
        }
    }
}


schema_limits = {
    "properties": {
        "generate_report": {
            "type": "object",
            "properties": {
                "max_failures": {
                    "type": "integer"
                },
                "wait_failures": {
                    "type": "integer"
                }
            },
            "minProperties": 1
        }
    }
}


schema_default = {
    "properties": {
        "directory": {
            "type": "string"
        },
        "timeformat": {
            "type": "string"
        },
        "mail": {
            "type": "object", 
            "properties": schema_mail["properties"], 
            "required": ["template", "subject", "recipients", "cc", "sender", "server"]
        },
        "healtcheck": {
            "type": "object", 
            "properties": schema_healthcheck, 
            "required": ["timediff_seconds"]
        },
        "limits": {
            "type": "object",
            "minProperties": 1
        }
    },
    "required": ["directory", "timeformat", "mail"]
}


schema_report = {
    "properties": {
        "name": {
            "type": "string"
        },
        "template": {
            "type": "string"
        },
        "scans": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "format": {
            "type": "string"
        }
    },
    "required": ["name", "template", "format"]
}


schema_profile = {
    "properties": {
        "directory": {
            "type": "string"
        },
        "timeformat": {
            "type": "string"
        },
        "mail": {
            "type": "object", 
            "properties": schema_mail["properties"]
        },
        "healtcheck": {
            "type": "object", 
            "properties": schema_healthcheck["properties"]
        },
        "limits": {
            "type": "object",
            "properties": schema_limits["properties"]
        },
        "scans": {
            "type": "array", 
            "items": {
                "type": "string"
            }
        },
        "reports": {
            "type": "array", 
            "items": {
                "type": "object", 
                "properties": schema_report["properties"]
            }
        }
    }, 
    "required": ["reports"]
}


schema_file = {
    "properties": {
        "default": {
            "type": "object", 
            "properties": schema_default["properties"],
            "required": ["directory", "timeformat", "mail"]
        },
        "profiles": {
            "type": "object", 
            "properties": schema_profile["properties"]
        }
    },
    "required": ["default", "profiles"]
}


class ProfileManager:
    def __init__(self, filename):
        self.logger = logging.getLogger("soc.apiclient.qualys.autoreport.ProfileManager")
        self.logger.info("loading profiles from {}".format(filename))
        with open(filename, 'r') as fd:
            self.src = json.load(fd)
        self.logger.info("validation profiles")
        jsonschema.validate(self.src, schema_file)
        self.logger.info("setting-up profiles")
        self.profiles = self.src["profiles"]
        self.default = self.src["default"]

    def profile(self, name):
        if name in self.profiles:
            self.logger.info("creating new profile from '{}'".format(name))
            return Profile(
                src=self.profiles[name],
                name=name,
                default_directory=self.default["directory"],
                default_timeformat=self.default["timeformat"],
                default_mail=self.default["mail"],
                default_healthcheck=self.default["healtcheck"],
                default_limits=self.default["limits"])
        raise Exception("no such profile: {}".format(name))


class Profile:
    def __init__(self, src, name, default_directory, default_timeformat, default_mail, default_healthcheck, default_limits):
        self.logger = logging.getLogger("soc.apiclient.qualys.autoreport.Profile")
        self.logger.info("validating profile")
        jsonschema.validate(src, schema_profile)
        self.logger.info("setting-up profile")
        # Name
        self.name = name
        # Directory
        self.directory = src.get("directory", default_directory)
        # Time format
        self.timeformat = src.get("timeformat", default_timeformat)
        # Mail
        mail_src = src.get("mail", default_mail)
        self.mail_template = mail_src.get("template", default_mail["template"])
        self.mail_template = self.mail_template is None and pkgrs(__name__, "static/report_ready.mail.html") or self.mail_template
        self.mail_subject = mail_src.get("subject", default_mail["subject"])
        self.mail_recipients = mail_src.get("recipients", default_mail["recipients"])
        self.mail_cc = mail_src.get("cc", default_mail["cc"])
        self.mail_sender = mail_src.get("sender", default_mail["sender"])
        self.mail_server = mail_src.get("server", default_mail["server"])
        # Health check
        healtcheck_src = src.get("healtcheck", default_healthcheck)
        self.healtcheck_timediff_seconds = healtcheck_src.get("timediff_seconds", healtcheck_src["timediff_seconds"])
        # Limits
        self.limits = default_limits
        # Scans
        self.scans = src.get("scans", [])
        # Reports
        self.reports = []
        for report in src["reports"]:
            self.reports.append({
                "name": report["name"],
                "template": report["template"],
                "scans": report.get("scans", self.scans),
                "format": report["format"]
            })
