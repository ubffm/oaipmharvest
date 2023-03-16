# Copyright 2020-2023, UB JCS, Goethe University Frankfurt am Main
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared functions"""
import logging
from itertools import product
from oaipmharvest.settings import get_spec_file


def get_logger(log_file=None):
    """Logging"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    io_handler = logging.StreamHandler()
    io_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s: %(levelname)s] %(message)s")
    io_handler.setFormatter(formatter)
    logger.addHandler(io_handler)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def compound_spec_resolver(item, settings):
    """Resolve compound specifications"""
    label = item.get("label")
    literal = item.get("literal")
    combine_file = item.get("combine_file")
    # append_file = item.get('append_file')
    # if sum(1 for element in (literal, combine_file, append_file) if element is not None) !=1:
    if sum(1 for element in (literal, combine_file) if element is not None) != 1:
        raise ValueError(
            "Only exactly one of literal, combine_file or append_file allowed."
        )
    if literal is not None:
        return [(label, literal)]
    if combine_file is not None:  # or append_file is not None:
        file = combine_file  # or append_file

        return [
            (item.get("label"), item.get("query"))
            for item in get_spec_file(settings["conf_base"] / file)
        ]
    raise ValueError("Unknown item:", item)


def iter_sets(settings, label_connector="/"):
    """Get the sets from file"""
    for _, values in settings.get("sets", {}).items():
        spec = values.get("spec")
        compound_spec = values.get("compound_spec")
        top_label = values.get("label", "")

        if spec is not None and compound_spec is not None:
            raise ValueError("Can not have both a spec and compound spec")
        if compound_spec is None:
            yield top_label, spec
        else:
            query_connector = compound_spec.get("connector", "")
            parts = []
            for part in compound_spec.get("parts", []):
                item = compound_spec_resolver(part, settings)
                parts.append(item)
            for combination in product(*parts):
                label = label_connector.join(
                    label for label, _ in combination if label and label is not None
                )
                label = label_connector.join((top_label, label))
                query = query_connector.join(
                    query for _, query in combination if query and query is not None
                )
                yield label, query
