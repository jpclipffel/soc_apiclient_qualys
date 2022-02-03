from setuptools import setup, find_packages


setup(name="soc_apiclient_qualys",
      version="1.0.0",
      description="SOC Qualys client API",
      author="Jean-Philippe Clipffel",
      packages=["soc", "soc.apiclient", "soc.apiclient.qualys", ],
      namespace_packages = ["soc", "soc.apiclient", ],
      entry_points={"console_scripts": ["soc.apiclient.qualys=soc.apiclient.qualys.__main__:main", ]},
      install_requires=["future_fstrings", "lxml", "jinja2", "requests", "argparse", "qualysapi", "tabulate", "jsonschema"],
      include_package_data=True
)
