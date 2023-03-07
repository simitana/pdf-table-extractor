from __future__ import annotations


class ExtractorError(Exception):
    pass


class UnsupportedFileError(ExtractorError):
    pass


class FileTooLargeError(ExtractorError):
    pass


class JobNotFoundError(ExtractorError):
    pass


class ExtractionFailedError(ExtractorError):
    pass
