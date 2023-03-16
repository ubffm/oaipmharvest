# oaipmharvest

## Description
oaipmharvest is a harvester for [OAI-PMH](https://www.openarchives.org/OAI/openarchivesprotocol.html) written in python
and based on [sickle](https://sickle.readthedocs.io) (for now). It's special focus lies on support for advanced
non-standard use cases. If you just need a the standard feature set, you might be better off with something more mature
and better tested.

The oaipmharvester will connect to a given OAI-endpoint and store its responses in a given output folder. It enables you
to make incremental requests from the given OAI-endpoint or even restrict the result set by a given date. In addition to
that, it provides several features to dynamically construct set specifiers from smaller parts.

**This is an alpha release. Use with caution.**

## Features
* Configuration via TOML
* Advanced configuration support for dynamic sets (for e.g. those supported by [BASE](http://oai.base-search.net/))

## Installation
After cloning the git repository locally, set up a virtual environment and run

```
pip install oaipmharvest
```

## Running

For running the application, you can call after the installation the CLI command `oaipm_harvest`, which also provides a help function
by calling `oaipm_harvester -h`.

```
usage: oaipm_harvest [-h] [--from FROM] [--until UNTIL] file

positional arguments:
  file                  Config file (TOML)

optional arguments:
  -h, --help            show this help message and exit
  --from FROM, -f FROM  Harvest only items that where published after the specified date
  --until UNTIL, -u UNTIL
                        Harvest only items that where published before the specified date
```

To harvest a specific OAI, you have to provide a conf-file. An example conf-file for the
most basic use case could be `conf/my-journal.conf` and would contain, for example:

```
endpoint_url = "https://www.contributions-to-entomology.org/oai/"
metadata_prefixes = ["marcxml"]
out_dir = "./out_cte"
use_sets = false
```

where

**endpoint\_url** is the OAI-base-URL you want to connect to.

**metadata\_prefixes** is a list of formats you want to download. The format is simply handed to the OAI-interface and, hence, it depends on the OAI-interface, if it supports the given format or not.

**out\_dir** is the directory, where all the downloaded data will be stored. If the given folder(s) do not exists, they will be created.

**use\_sets** false 

## Licence

All parts of this code are copyrighted by the University Library JCS, Frankfurt a. M. The project is made available
under the Mozilla Public License 2.0.

## Acknowledgement  
This is a project created and maintained by the [Specialised Information Service for Linguistics](https://www.linguistik.de/en/)
at the [University Library J. C. Senckenberg](https://www.ub.uni-frankfurt.de/) and funded by the German Research Foundation (DFG; project identifier [326024153](https://gepris.dfg.de/gepris/projekt/326024153?language=en)).

