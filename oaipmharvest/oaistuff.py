# Copyright 2020-2023, UB JCS, Goethe University Frankfurt am Main
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""OAI stuff"""
import datetime
from time import sleep
from lxml import etree
from sickle import Sickle, oaiexceptions, iterator, models
import arrow

from oaipmharvest.commons import get_logger

DEFAULT_METADATA_PREFIX = "oai_dc"
OAI_NAMESPACE = "http://www.openarchives.org/OAI/2.0/"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"

NAMESPACES = {
    "oai": OAI_NAMESPACE,
    "dc": DC_NAMESPACE,
}


# TODO: Resumption token should work with dates
# TODO: Klammerung schön einbauen
def iter_records(
    query,
    endpoint,
    kwargs=None,
    logger=None,
    metadata_prefix=DEFAULT_METADATA_PREFIX,
    date_from=None,
    date_until=None,
):
    """Iter oai records."""
    if kwargs is not None and "resumptionToken" in kwargs:
        try:
            records = endpoint.ListRecords(**kwargs)
        except oaiexceptions.BadResumptionToken as e:
            if logger is not None:
                logger.critical(
                    "The resumption token has expired"
                    " (or is otherwise invalid). Please remove manually."
                )
                raise SystemExit
            else:
                raise e
        except oaiexceptions.NoRecordsMatch:
            if logger is not None:
                logger.warn("No records.")
            return None, None
        if not hasattr(records, "resumption_token") or records.resumption_token is None:
            if logger is not None:
                logger.warn("No resumption token.")
            return
    else:
        params = {"metadataPrefix": metadata_prefix}
        if query is not None:
            params["set"] = query
        if date_from is not None:
            params["from"] = date_from
        if date_until is not None:
            params["until"] = date_until
        try:
            records = endpoint.ListRecords(**params)
        except oaiexceptions.NoRecordsMatch:
            if logger is not None:
                logger.warn("No records.")
            return
    if records.resumption_token is not None:
        list_size = records.resumption_token.complete_list_size
        if logger is not None:
            logger.info("Records: %s", list_size)
    while True:
        try:
            try:
                batch = records.next()
            except oaiexceptions.NoRecordsMatch:
                logger.warn("No records.")
                yield None, None
                return
            yield batch, records.resumption_token
        except StopIteration:
            return


def prepare_date(date, template="YYYY-MM-DD"):
    """Date preparation helper."""
    tmp = arrow.get(date)
    formatted = tmp.format(template)
    return formatted


def get_response_date(file, func=None):
    """Parse and return response date."""
    tree = etree.parse(str(file))
    response_date = tree.xpath("oai:responseDate", namespaces=NAMESPACES)
    assert len(response_date) == 1
    text = response_date[0].text
    if func is not None:
        date = func(text)
    else:
        date = text
    return date


def get_metadata_formats(s):
    """Get metadata formats"""
    # Workaround because OAIResponseIterator apparently doesnt work well with ListMetadataFormats.
    result = {}
    response = next(s.ListMetadataFormats())
    formats = [
        models.MetadataFormat(element)
        for element in response.xml.xpath(
            "./base_dc:ListMetadataFormats/base_dc:metadataFormat",
            namespaces={"base_dc": "http://www.openarchives.org/OAI/2.0/"},
        )
    ]
    for mdf in formats:
        result[mdf.metadataPrefix] = mdf.metadataNamespace
    return result


class Endpoint:
    """Encapsulate an OAI Endpoint"""

    def __init__(
        self,
        endpoint_url,
        metadata_prefixes=None,
        logger=None,
        settings=None,
        **request_args
    ):
        if logger is None:
            self.logger = get_logger()
        else:
            self.logger = logger
        if settings is None:
            raise ValueError("No settings.")
        self.endpoint_url = endpoint_url
        self.result_dir = ""
        self.metadata_prefixes = (
            metadata_prefixes
            if metadata_prefixes is not None
            else [DEFAULT_METADATA_PREFIX]
        )
        self.settings = settings
        self.sickle = Sickle(
            self.endpoint_url, iterator=iterator.OAIResponseIterator, **request_args
        )
        self.identity = self.sickle.Identify()
        self._crawl_date = datetime.date.today()

    @property
    def metadata_formats(self):
        """Supported metadata formats"""
        return get_metadata_formats(self.sickle)

    def greet(self):
        """Print some infos about the repo."""
        self.logger.info("Repository: %s", self.identity.repositoryName)
        self.logger.info("Base Url: %s", self.identity.baseURL)
        self.logger.info("Admin email: %s", self.identity.adminEmail)
        self.logger.info("OAI version: %s", self.identity.protocolVersion)
        self.logger.info("Granularity: %s", self.identity.granularity)
        self.logger.info("Deleted records: %s", self.identity.deletedRecord)
        self.logger.info("Earliest datestamp: %s", self.identity.earliestDatestamp)
        self.logger.info(
            "Supported metadata prefixes: %s", ", ".join(self.metadata_formats.keys())
        )
        self.logger.info("Using prefixes: %s", ", ".join(self.metadata_prefixes))
        if hasattr(self.identity, "compression"):
            self.logger.info("Compression: %s", self.identity.compression)
        if hasattr(self.identity, "description"):
            if self.identity.description is not None:
                self.logger.info("Description: %s", self.identity.description)

    def to_file(self, batch, logger=None, meta=None):
        """The basic dispatcher. Put stuff to files."""
        if meta is None:
            raise ValueError
        if logger is None:
            logger = self.logger
        logger.info("Write batch: %s", meta["counter"])
        my_id = meta["cursor"] if meta["cursor"] is not None else meta["counter"]
        file_name = self.settings["file_template"].format(
            date=str(self._crawl_date), mdf=meta["prefix"], id=my_id
        )
        with (meta["result_path"] / file_name).open("wb") as fh:
            root = batch.xml.getroottree()
            root.write(fh, pretty_print=True, xml_declaration=True, encoding="utf-8")

    def harvest(self, oai_set=None, date_from=None, date_until=None, dispatch=None):
        """Harvest."""
        if dispatch is None:
            dispatch = self.to_file
        result_dir = oai_set[0] if oai_set is not None else "UNSPECIFIED-SET"
        self.result_dir = result_dir
        result_path = self.settings["out_dir"] / result_dir
        if date_from:
            result_path /= str(date_from)
        if not result_path.exists():
            result_path.mkdir(parents=True, exist_ok=True)
        resumption_file = result_path / self.settings["resumption_file"]
        kwargs = {}
        if resumption_file.exists():
            with resumption_file.open("rt", encoding="utf8") as fh:
                token = fh.read()
                self.logger.info("Resume from existing token.")
                kwargs = {"resumptionToken": token}
        elif len(list(result_path.glob("*"))) > 0:
            self.logger.info("Skip.")
            return
        for prefix in self.metadata_prefixes:
            batches = iter_records(
                oai_set[1] if oai_set is not None else oai_set,
                self.sickle,
                kwargs=kwargs,
                logger=self.logger,
                metadata_prefix=prefix,
                date_from=date_from,
                date_until=date_until,
            )
            for i, item in enumerate(batches, 1):
                batch, resumption_token = item
                if (
                    hasattr(resumption_token, "token")
                    and resumption_token.token is not None
                ):
                    with resumption_file.open("wt", encoding="utf8") as fh:
                        fh.write(resumption_token.token)
                else:
                    if resumption_file.exists():
                        resumption_file.unlink()
                        # continue
                cursor = None
                if resumption_token is not None and hasattr(resumption_token, "cursor"):
                    cursor = resumption_token.cursor
                    if cursor is not None:
                        self.logger.info("Next cursor: %s", cursor)
                meta = {
                    "cursor": cursor,
                    "prefix": prefix,
                    "counter": i,
                    "set": oai_set,
                    "result_path": result_path,
                }
                dispatch(batch, meta=meta)
                sleep(self.settings["harvest_delay"])
            if resumption_file.exists():
                raise ValueError("There should be no resumption Token.")
