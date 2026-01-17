# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.
import errno
import hashlib
import os
from binascii import hexlify
from time import time as now_s

import config
from bridge import subprocess
from util.diagnostics import loggable
from util.misc import plu, unlink_quietly
from util.singleton import singleton
from util.stream_wrapper import stream_wrapper_from_url


class FileChecksumError(Exception):
    def __init__(self, expected: str, actual: str, size: int):
        self.__expected = expected
        self.__actual = actual
        self.__size = size

    def __str__(self):
        return f"size={self.__size}, expected_checksum={self.__expected}, actual_checksum={self.__actual}"


@singleton
@loggable
class ZigbeeFwFetcher:
    """
    Fetches firmware files from provided URLs and stores them in the configured location.

    Multiple firmwares can be cached and returned without re-downloading. The total
    starage space is bound by a configuration parameter.

    The firmware file MD5 checksum is used as a key.
    """

    def __init__(self):
        self.__prepare_storage_folder()
        self.__populate_cache()
        self.__cleanup()

    def __prepare_storage_folder(self):
        """Recursively create the storage path."""
        parts = config.fw_repository_path.lstrip("/").split("/")
        for n in range(1, len(parts) + 1):
            path = "/" + "/".join(parts[:n])
            try:
                os.mkdir(path)
            except OSError as ose:
                if ose.errno != errno.EEXIST:
                    self._logger.error(
                        "Unable to create firmware storage folder %s: %s(%s)", path, type(ose).__name__, str(ose)
                    )
                    raise

    def __verify_cached_file(self, file_path: str, expected_checksum: str):
        self._logger.debug("Verifying cached firmware file %s", file_path)
        digest = hashlib.md5()
        size = 0
        with open(file_path, "rb") as file:
            preallocated_chunk = bytearray(config.libflasher_chunk_size)
            while True:
                n = file.readinto(preallocated_chunk)
                size += n
                if n:
                    digest.update(memoryview(preallocated_chunk)[0:n])
                else:
                    checksum = hexlify(digest.digest()).decode().strip()
                    if checksum != expected_checksum:
                        raise FileChecksumError(expected_checksum, checksum, size)
                    break

    def __populate_cache(self):
        """Load the preexisting files in the storage location."""
        self.__cache = []
        total_size = 0
        for file_name, *_ in os.ilistdir(config.fw_repository_path):
            if file_name not in (".", ".."):
                file_path = f"{config.fw_repository_path}/{file_name}"
                try:
                    *_, size, _, _, ctime = os.stat(file_path)
                    self.__verify_cached_file(file_path, file_name)
                    self.__cache += [(ctime, size, file_name)]
                    total_size += size
                except Exception as ex:
                    self._logger.warning(
                        "Something wrong with %s: %s(%s), removing", file_path, type(ex).__name__, str(ex)
                    )
                    unlink_quietly(file_path)
        self.__cache.sort()
        self._logger.info(
            "Instantiated, %s (%s) in the firmware cache", plu(len(self.__cache), "file"), plu(total_size, "byte")
        )

    def __cleanup(self):
        """
        Trim the storage location not to exceed the configured maximum size.

        Oldest files are removed first.
        """
        total_size = sum(map(lambda f: f[1], self.__cache))
        budget = config.dynamic["fw_repository_budget"]
        while total_size > budget and len(self.__cache) > 1:
            *_, size, file_name = self.__cache[0]
            file_path = f"{config.fw_repository_path}/{file_name}"
            self._logger.info(
                "Firmware cache (%d bytes) size exceeds budget (%d bytes), removing %s", total_size, budget, file_path
            )
            try:
                os.unlink(file_path)
            except Exception as ex:
                self._logger.warning("Unable to remove %s: %s(%s)", file_path, type(ex).__name__, str(ex))
            total_size -= size
            del self.__cache[0]

    def __find_in_cache(self, checksum: str) -> str:
        for *_, file_name in self.__cache:
            if file_name == checksum:
                return f"{config.fw_repository_path}/{file_name}"
        return None

    def delete(self, checksum: str):
        """Purges the image with the provided checksum from the image cache."""
        for n in range(len(self.__cache)):  # pylint: disable=consider-using-enumerate
            *_, file_name = self.__cache[n]
            if file_name == checksum:
                index = n
                break
        else:
            return
        file_path = f"{config.fw_repository_path}/{file_name}"
        self._logger.info("Removing %s from cache", file_path)
        del self.__cache[index]
        try:
            os.unlink(file_path)
        except Exception as ex:
            self._logger.warning("Unable to remove %s: %s(%s)", file_path, type(ex).__name__, str(ex))

    async def fetch(self, url: str, checksum: str) -> tuple:
        """
        Fetches the firmware image with the provided checksum from
        the provided URL or from cache and returns a tuple (file_path, cached).

        If the URL points to a file, then it is simply moved into the cache.
        """
        if url.startswith("file://"):
            return await self.__fetch_from_file(url[len("file://") :], checksum)
        return await self.__fetch_from_url(url, checksum)

    async def __fetch_from_file(self, url: str, checksum: str) -> tuple:
        try:
            if file_path := self.__find_in_cache(checksum):
                self._logger.info("File %s is already in cache, location=%s", url, file_path)
                return file_path, True
            file_path = f"{config.fw_repository_path}/{checksum}"
            self._logger.info("Storing %s into cache, destination=%s", url, file_path)
            os.rename(url, file_path)
            try:
                subprocess.run(f"fsync {file_path}")
            except Exception as ex:
                self._logger.warning("Syncing FS failed due to %s(%s)", type(ex).__name__, str(ex))
            *_, size, _, _, _ = os.stat(file_path)
            self.__cache.append((now_s(), size, checksum))
            self.__cleanup()
            return file_path, False
        finally:
            unlink_quietly(url)

    async def __fetch_from_url(self, url: str, checksum: str) -> tuple:
        if file_path := self.__find_in_cache(checksum):
            self._logger.info("Firmware image from %s is already in cache, location=%s", url, file_path)
            return file_path, True
        file_path = f"{config.fw_repository_path}/{checksum}"
        self._logger.info("Fetching firmware image from %s, checksum=%s, destination=%s", url, checksum, file_path)
        stream = await stream_wrapper_from_url(url, config.dynamic["fw_repository_budget"])
        async with stream:
            try:
                with open(file_path, "wb") as file:
                    downloaded_size = await stream.stream(consumer=file.write, checksum=checksum)
                try:
                    subprocess.run(f"fsync {file_path}")
                except Exception as ex:
                    self._logger.warning("Syncing FS failed due to %s(%s)", type(ex).__name__, str(ex))
                self.__cache.append((now_s(), downloaded_size, checksum))
                self.__cleanup()
                return file_path, False
            except Exception:
                unlink_quietly(file_path)
                raise
