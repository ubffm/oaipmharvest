# Copyright 2020-2023, UB JCS, Goethe University Frankfurt am Main
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Settings and configurations."""
import argparse
import pathlib

import toml
from voluptuous import Schema, Required, All

DEFAULT_SETTINGS = {
    "metadata_prefixes": ["oai_dc"],
    "file_template": "{date}__{mdf}__{id:0>12}.xml",
    "harvest_delay": 3,
    "resumption_file": "last_resumption_token.txt",
}


def get_args():
    """Cli argument handling."""
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=pathlib.Path, help="Config file (TOML)")
    parser.add_argument(
        "--from",
        "-f",
        help="Harvest only items that where published after the specified date",
    )
    parser.add_argument(
        "--until",
        "-u",
        help="Harvest only items that where published before the specified date",
    )
    return parser.parse_args()


def validate_settings(settings):
    """Validate the settings file"""
    schema = Schema(
        {
            Required("endpoint_url"): str,
            Required("out_dir"): str,
            Required("use_sets"): bool,
            Required("metadata_prefixes"): All(list, min=1),
            # usage of TOML date parser complicates things at this point. Just treat them as strings _despite_ the
            # fact that TOML supports them and even in the format specified by OAI
            "from": str,
            "until": str,
            "day_steps": int,
            "proxies": dict,
            "sets": dict,
        }
    )
    return schema(settings)


def validate_spec(spec):
    """Validate the compound statements."""
    schema = Schema({Required("queries"): All(list, min=1)})

    return schema(spec)


def get_settings(file):
    """Load the settings."""
    settings = {}
    # make sure it's a copy, not a clone
    settings.update(DEFAULT_SETTINGS)
    data = toml.load(file)
    _ = validate_settings(data)
    data["out_dir"] = pathlib.Path(data["out_dir"])
    # config in files take precedence
    settings.update(data)
    settings["conf_base"] = file.parent.absolute()
    return settings


def get_spec_file(file):
    """Load the specification"""
    data = toml.load(file)
    _ = validate_spec(data)
    return data["queries"]
