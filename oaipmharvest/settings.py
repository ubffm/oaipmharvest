# Copyright 2020-2025, UB JCS, Goethe University Frankfurt am Main
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Settings and configurations."""
import argparse
import os
import pathlib
from hashlib import blake2b

try:
    import tomllib
except ImportError:
    import tomli as tomllib


from voluptuous import Schema, Required, All

DEFAULT_SETTINGS = {
    "metadata_prefixes": ["oai_dc"],
    "file_template": "{crawl_id}__{date}__{mdf}__{id:0>12}.xml",
    "harvest_delay": 3,
    "resumption_file": "last_resumption_token.txt",
    "timeout": 60,
    "max_retries": 3,
}


class SettingsError(Exception):
    pass


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


def get_file_hash(file):
    with file.open("rb") as fh:
        content = fh.read()
    hash_value = blake2b(content)
    return hash_value.hexdigest()


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
            "accept_encoding": str,
            "sets": dict,
            "harvest_delay": int,
            "max_retries": int,
            "timeout": float,
            "http_cookie_env_var": str,
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
    with file.open("rb") as fh:
        data = tomllib.load(fh)
    _ = validate_settings(data)
    data["out_dir"] = pathlib.Path(data["out_dir"])
    # config in files take precedence
    settings.update(data)
    settings["conf_base"] = file.parent.absolute()
    settings["config_hash"] = get_file_hash(file)
    if "http_cookie_env_var" in settings:
        cookie_name = settings["http_cookie_env_var"]
        try:
            cookie_value = os.environ[cookie_name]
        except KeyError:
            raise SettingsError("Can not find environment variable for cookie")
        settings["cookies"] = {cookie_name: cookie_value}
    return settings


def get_spec_file(file):
    """Load the specification"""
    with file.open("rb") as fh:
        data = tomllib.load(fh)
    _ = validate_spec(data)
    return data["queries"]
