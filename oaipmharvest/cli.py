#!/usr/bin/env python3
# Copyright 2020-2023, UB JCS, Goethe University Frankfurt am Main
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Commandline interface to the OAI-PMH harvester."""
import datetime
import arrow
from oaipmharvest.commons import get_logger, iter_sets
from oaipmharvest.settings import get_args, get_settings
from oaipmharvest.oaistuff import Endpoint


def iter_dates(date_from, date_until, day_steps):
    """Iter dates for selective harvesting"""
    target_date_from = date_from
    target_date_until = date_until
    date_until = target_date_from + datetime.timedelta(days=1) * day_steps

    while date_until < target_date_until:
        yield date_from, date_until
        date_from, date_until = (
            date_until,
            date_until + datetime.timedelta(days=1) * day_steps,
        )
        date_until = min(date_until, target_date_until)


def main():
    """Where the harvest begins."""
    args = get_args()

    settings = get_settings(args.file)
    # TODO: Refactor!
    logger = get_logger(
        settings["out_dir"]
        / "oai_{date}.log".format(date=str(datetime.datetime.now()).replace(" ", "_"))
    )
    if not settings["out_dir"].exists():
        settings["out_dir"].mkdir()
    request_args = {}
    if "proxies" in settings:
        request_args["proxies"] = settings["proxies"]
    oai_sets = iter_sets(settings)

    endpoint = Endpoint(
        endpoint_url=settings["endpoint_url"],
        metadata_prefixes=settings["metadata_prefixes"],
        logger=logger,
        settings=settings,
        **request_args
    )

    endpoint.greet()
    if "day_steps" in settings:
        if "from" not in settings or "until" not in settings:
            raise ValueError(
                '"until" and "from" must be specified if "day_steps" is used.'
            )
        try:
            if settings["use_sets"]:
                for oai_set in oai_sets:
                    for date_from, date_until in iter_dates(
                        arrow.get(settings["from"]),
                        arrow.get(settings["until"]),
                        settings["day_steps"],
                    ):
                        oai_params = {
                            "oai_set": oai_set,
                            "date_from": date_from.isoformat(),
                            "date_until": date_until.isoformat(),
                        }
                        logger.info("Set: %s", oai_set[0])
                        endpoint.harvest(**oai_params)
        except KeyboardInterrupt:
            print("Manual stop.")
    else:
        try:
            oai_params = {}
            if "from" in settings:
                oai_params["date_from"] = settings["from"]
            if "until" in settings:
                oai_params["date_until"] = settings["until"]
            if settings["use_sets"]:
                for oai_set in oai_sets:
                    oai_params["oai_set"] = oai_set
                    logger.info("Set: %s", oai_set[0])
                    endpoint.harvest(**oai_params)
            else:
                endpoint.harvest(**oai_params)
        except KeyboardInterrupt:
            print("Manual stop.")


if __name__ == "__main__":
    main()
