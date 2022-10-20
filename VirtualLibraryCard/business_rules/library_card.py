from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from os import linesep
from random import random
from threading import Thread
from typing import IO, Any, Dict, Generator, List, Set, Tuple

from django.core.files.storage import FileSystemStorage
from django.db.utils import IntegrityError

from virtual_library_card.logging import log
from virtual_library_card.sender import Sender
from VirtualLibraryCard.models import CustomUser, Library, LibraryCard


class LibraryCardRules:
    @classmethod
    def new_card(
        cls, user: CustomUser, library: Library, number: str = None
    ) -> Tuple[LibraryCard, bool]:
        """Generate a new card only of a card does not exist for this user and library
        Also send the welcome email"""
        existing_library_card: LibraryCard = LibraryCard.objects.filter(
            user=user, library=library
        ).first()
        if existing_library_card is None:
            card = CustomUser.create_card_for_library(library, user, number=number)
            card.save()
            Sender.send_user_welcome(library, user, card.number)
            return card, True
        return existing_library_card, False


class LibraryCardBulkUpload:
    REQUIRED_CSV_HEADERS = ["id", "first_name", "email"]
    OPTIONAL_CSV_HEADERS = ["last_name", "city", "us_state", "zip"]
    FOLDER = "bulk_upload_csvs"
    # Write uploaded CSVs to the local system since they are temporary files
    # Must change this in the future if and when implementing async out-of-band queues and job servers
    storage_class = FileSystemStorage

    @classmethod
    def bulk_upload_csv(
        cls,
        library: Library,
        fileio: IO,
        admin_user: CustomUser = None,
        _async: bool = False,
    ) -> LibraryCardBulkUpload:
        """Bulk upload a CSV of library users with information enough to generate cards
        Returns nothing because it will be an async task eventually"""
        instance = cls(library, fileio, admin_user=admin_user, _async=_async)
        instance.process()
        return instance

    def __init__(
        self,
        library: Library,
        fileio: IO,
        admin_user: CustomUser = None,
        _async: bool = True,
    ) -> None:
        self.library = library
        self.fileio = fileio
        self.admin_user = admin_user
        self._async = _async
        self._async_thread = None

    def process(self):
        """Process the uploaded file in the backend
        This should
        - read the csv line by line
        - validate the data for duplicate and headers
        - Kick off the process in either an async or sync manner
        """

        if not self.library.bulk_upload_prefix:
            raise BulkUploadLibraryException("Library has no upload prefix")

        if not self.library.allow_bulk_card_uploads:
            raise BulkUploadLibraryException("Library does not allow bulk uploads")

        csv_lines = list(iter_clean_lines(self.fileio))
        reader = csv.DictReader(csv_lines)
        self.validate_data(reader)

        if self._async:
            # We must write the csv io contents to something available to a thread
            storage = self.storage_class()
            t = datetime.now().timestamp()
            filename = storage.get_available_name(
                f"{self.FOLDER}/bulk-upload-csv-{t}-{random()}.csv"
            )

            # Saving the file first ensures the directory structure is created
            storage.save(filename, BytesIO(b""))

            with storage.open(filename, mode="w") as fp:
                for line in csv_lines:
                    fp.write(line)
                    fp.write(linesep)
            # in async mode we deal with written files, not file pointers
            self._async_thread = Thread(
                target=self._process, args=[filename], daemon=False
            )
            self._async_thread.start()
        else:
            # If not async, we simply run the process
            self.fileio.seek(0)
            self._process(self.fileio)

    def _process(self, csv_file: IO | str):
        """The actual process of bulk creating csv based users and cards
        It assumes it may be an async method
        If should:
        - Read the file or io object for the csv data
        - Create a new user for each line, or update the existing user
        - Create a card, or use an existing card per user
        - Send out a verification email for new users
        - Send out the report for the upload
        - Delete the CSV upload file, if present
        """
        if type(csv_file) is str:
            storage = self.storage_class()
            with storage.open(csv_file, "r") as fp:
                csv_lines = list(iter_clean_lines(fp))
        else:
            csv_lines = list(iter_clean_lines(csv_file))

        reader = csv.DictReader(csv_lines)
        results: List[Dict[str, Any]] = []
        for item in reader:
            try:
                is_new = False
                user = CustomUser.objects.filter(
                    email=item["email"], library=self.library
                ).first()
                if not user:
                    is_new = True
                    user = CustomUser(
                        first_name=item["first_name"],
                        email=item["email"],
                        library=self.library,
                        email_verified=False,
                    )
                else:
                    # If the user exists, just update the data
                    user.first_name = item["first_name"]

                # Set the additional data points, if present
                for name in self.OPTIONAL_CSV_HEADERS:
                    if name in item and item[name]:
                        setattr(user, name, item[name])

                try:
                    user.save()
                except IntegrityError as ex:
                    # Switch out the error for readability
                    log.exception(
                        f"Could not save user during bulk upload: {user.email}"
                    )
                    raise Exception(
                        f"Email {user.email} already exists in the system for a different library."
                    )

                user_id = item.pop("id")

                prefix = self.library.bulk_upload_prefix
                card, _ = LibraryCardRules.new_card(
                    user, self.library, number=prefix + user_id
                )
                log.log(f"Created user and card for {user.email}: {card.number}")
                results.append({"card number": card.number, "error": "", **item})
            except Exception as ex:
                log.error(f"Could not create card or user: {ex}")
                results.append({"card number": "", "error": str(ex), **item})

        if type(csv_file) is str and storage.exists(csv_file):
            storage.delete(csv_file)

        self._send_results(results)

    def _send_results(self, results: List[Dict[str, Any]]):
        """Send the results of the upload to the responsible admin
        The results are sent as an attachment to the email
        due to the possibly large size of the report"""
        if not self.admin_user:
            log.error("No admin user to send the upload report to!")
            return

        # Write the report as an attachment, must be locally stored in order to attach to emails
        storage = FileSystemStorage()
        t = datetime.now().timestamp()
        filename = storage.get_available_name(f"upload-report-{t}-{random()}.csv")

        try:
            report_fields = ["first_name", "email", "card number", "error"]
            storage.save(filename, BytesIO(b""))
            with storage.open(filename, mode="w") as fp:
                writer = csv.DictWriter(fp, fieldnames=report_fields)
                writer.writeheader()
                # filter out only the report fields
                to_send = map(lambda x: {key: x[key] for key in report_fields}, results)
                writer.writerows(to_send)

            Sender.send_bulk_upload_report(
                self.admin_user.email, self.library, storage.path(filename)
            )
        except Exception as ex:
            log.error(f"Could not send upload report: {ex}")
        finally:
            # Delete the report file after sending, or failing
            if storage.exists(filename):
                storage.delete(filename)

    def validate_data(self, csvreader: csv.DictReader) -> bool:
        """Validate csv data for bad headers or duplicate items. Throws exceptions where required."""
        headers = csvreader.fieldnames
        if not set(headers).issuperset(self.REQUIRED_CSV_HEADERS):
            # Headers are not valid
            raise BulkUploadBadHeadersException(
                f"The uploaded files headers were not valid. The headers must contain all of {self.REQUIRED_CSV_HEADERS}."
            )

        # Check for duplicate data
        emails = set()
        ids = set()
        duplicates = {"emails": set(), "ids": set()}
        for item in csvreader:
            email = item["email"]
            id = item["id"]

            if email in emails:
                duplicates["emails"].add(email)
            if id in ids:
                duplicates["ids"].add(id)

            emails.add(email)
            ids.add(id)

        if duplicates["emails"] or duplicates["ids"]:
            raise BulkUploadDuplicatesException(duplicates=duplicates)

        return True


def iter_clean_lines(io: IO) -> Generator[str, None, None]:
    """Iterate over an IO object and ignore blank lines
    This is to specifically ignore empty last lines in csvs"""
    line: str | bytes
    for line in io.readlines():
        if type(line) == bytes:
            line = line.decode()
        if line.isspace():
            continue
        yield line.strip()


class BulkUploadBadHeadersException(Exception):
    pass


class BulkUploadLibraryException(Exception):
    pass


@dataclass
class BulkUploadDuplicatesException(Exception):
    duplicates: Dict[str, Set[str]]
