# SOC / API Client / Qualys

`soc_apiclient_qualys` is a Python package (2.7) designed to interact
with a Qualys API server.


## Installation
It is **highly recommended** to install the tool within a virtual environment.

### Dependencies
* `python2.7`: Python interpreter in version 2.7
* `pip`: Python package manager

### Virtual environment
* Install `virtualenv` on the target system if needed: `pip2 install virtualenv`
* Create a virtual environment: `python2 -m virtualenv <path/to/your/venv>`
* Activate the virtual environment: `source <path/to/your/venv>/bin/activate`

### Install the package
If you wish to keep the package up-to-date with the GIT repository:
* Clone the repository: run `git clone https://scm.tld/soc_apiclient_qualys.git`
* Install the package: run `pip2 install -e soc_apiclient_qualys`

Otherwise:
* Install the package: run `pip2 install <path/to/package>`


## Usage
The tools provides several CLI commands to interact with a Qualys server.

### CLI usage
Syntax:
```
soc.apiclient.qualys [-h]
                     --config <path/to/qrc.ini>
                     <command> [command arguments]
```

Arguments:
* `-h`: Show help.
* `--config`: Path to Qualys API configuration file. Mandatory.

### `list` command
This command list the requested Qualys objects.

Syntax:
```
... list [--filter <regex>]
         <scans|reports|templates>
```

Arguments:
* `--filter`: Regex filter on the object name.
* `<scans|reports|templates>`: Select the object type to list.

### `report` command
This command launch a report generation.
It the command succeeds, the new report ID will be displayed.

Syntax:
```
... report --name <name of the new report>
           --template <qualys report template name>
           --scans <scan_name_1> [scan_name_2] [...]
```

Arguments:
* `--name`: Name of the new report to generate.
* `--template`: Name of the Qualys's report's template. One can use the
command `list templates` to obtain the list of available templates.
* `--scans`: One or more Qualys's scans name to include in the report. One can
use the command `list scans` to obtain the list of available scans.

**Note on scans version**  
The tool will automatically select the latest available version for each given
scan name.

### `download` command
This command download a generated report.

Syntax:
```
... download --name <report name>
             [--directory <path/to/download/directory>]
             [--filename <downloaded file name>]
```

Arguments:
* `--name`: Name of the report to download.
* `--directory`: Specify where the report must be saved.
* `--filename`: Specify under which name the report file must be saved.

**Note on reports version**  
The tool will automatically select the latest available report version.

### `autoreport` command
This command automates the report generation, download and notification.

Syntax:
```
... autoreport [--profiles <path/to/profiles.json>] <profile name>
```

Arguments:
* `--profiles`: Path to the `profiles` configuration file (see next section)
* `profile name`: Name of the profile to use.

**Note on scans version**  
The tool will automatically select the latest available version for each given
scan name.

**Note on reports version**  
The tool will automatically select the latest available report version.

#### The `profiles.json` configuration file
By default, the `autoreport` command will use the package's `profiles.json`
file. The file use the following structure:
```json
{
  "default": {},
  "profiles": {}
}
```

##### `default` node
This node defines the default attributes used for report generation and
notification. All the attributes may be overloaded in the `profile` sections.
**ALL attrbibutes are mandatory !**
```json
{
  "default": {
    "directory": "",
    "mail": {
      "subject": "",
      "template": null,
      "recipients": [""],
      "cc": [""],
      "sender": "",
      "server": ""
    }
  }
}
```
* `.default.directory`: Reports' generation directory.
* `.default.mail`: E-mail notification configuration.
* `.default.mail.subject`: E-mail subject.
* `.default.mail.template`: E-mail template file. If `null`, refers to
package's default notification template.
* `.default.mail.recipients`: E-mail recipients addresses.
* `.default.mail.cc`: E-mail CC addresses.
* `.default.mail.sender`: E-mail sender address.
* `.default.mail.server`: E-mail gateway.

##### `profiles` node
This node defines the profiles availalble for the `autoreport` command.
```json
{
  "profiles": {
    "name": {
      "directory": "",
      "mail": {
        "subject": "",
        "template": null,
        "recipients": [""],
        "cc": [""],
        "sender": "",
        "server": ""
      },
      "scans": [""],
      "reports": [
        {"name": "", "template": ""}
      ]
    }
  }
}
```
* `.name`: Name of the profile.
* `.name.directory`: Reports' generation directory. Optional.
* `.name.mail`: E-mail notification configuration. Optional.
* `.name.mail.*`: E-mail notification attributes. All are optionals.
* `.name.scans`: List of scans. Could also be defined per-report under
`.name.reports.*.scans`.
* `.name.reports`: List of reports.
* `.name.reports.*.name`: Report's name.
* `.name.reports.*.template`: Report's template name.
* `.name.reports.*.scans`: List of report's scans name. Could also be defined
  globally under `.name.scans` (common to all reports).
