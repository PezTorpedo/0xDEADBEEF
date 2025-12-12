# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import json
import re
import struct
from time import time, time_ns

import config
from bridge import hal
from component import ComponentEvent
from util.diagnostics import loggable
from util.http_server import HttpServer, Response
from util.misc import pretty_interval, unlink_quietly
from util.mqtt_proxy import MqttError, MqttProxy
from util.stream_wrapper import StreamSpy, stream_wrapper_from_reader
from util.stream_wrapper_base import StreamSizeError

import huettp
from flasher import (
    FW2_DONT_REQUIRE_WHITELIST,
    SW_ERROR_GROUP_IMAGE_INCOMPLETE,
    SW_ERROR_GROUP_IMAGE_INVALID,
    SW_ERROR_GROUP_IMAGE_TOO_BIG,
    SW_ERROR_GROUP_MASK,
    SW_ERROR_GROUP_VERSION_INVALID,
)

COMMON_RESPONSE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, post-check=0, pre-check=0",
    "Pragma": "no-cache",
    "Expires": "Mon, 1 Aug 2011 09:00:00 GMT",
    "Connection": "close",
    "Access-Control-Max-Age": "0",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, hue-whitelist",
}

# The timeout for the whitelist authentication request.
AUTH_TIMEOUT = 2.0

# Images of up to this size can squeeze through unauthenticated.
SNEAKY_IMAGE_SIZE = 2048

# The sideloading window is open for that many seconds after the link button press.
LINK_BUTTON_WINDOW = 60

AUTH_ALLOW_BUTTON_WHITELIST_BYPASS = 0x80

# Zigbee Cluster Library Specification 11.4.2 - OTA Header Format
OTAU_HEADER_SPEC = "<IHHHHHI"

# Zigbee Cluster Library Specification 11.4.2.1 - OTA Upgrade File Identifier
OTAU_MAGIC = 0x0BEEF11E

# Zigbee Cluster Library Specification 11.4.2.2 - OTA Header Version
OTAU_HEADER_VERSION = 0x0100


@loggable
class FrontendSideload:
    def __init__(self, mqtt: MqttProxy, event_sink):
        bind_address, port = config.sideload_bind_address, config.sideload_port
        endpoint, auth_endpoint = config.sideload_endpoint, config.sideload_auth_endpoint
        self._logger.info("Main endpoint at http://%s:%d, matching %s", bind_address, port, endpoint)
        self._logger.info("Authentication endpoint at http://%s:%d, matching %s", bind_address, port, auth_endpoint)
        self._logger.info(
            "Nanoconfig endpoint at http://%s:%d, matching %s", bind_address, port, config.nanoconfig_endpoint
        )
        self.__http_server = HttpServer(bind_address, port)
        self.__http_server.register_endpoint("GET", endpoint, self.__handle_device_nanoconfig_request)
        self.__http_server.register_endpoint("GET", config.nanoconfig_endpoint, self.__handle_nanoconfig_request)
        self.__http_server.register_endpoint("OPTIONS", endpoint, self.__handle_options_request)
        self.__http_server.register_endpoint("OPTIONS", config.nanoconfig_endpoint, self.__handle_options_request)
        self.__http_server.register_endpoint("POST", endpoint, self.__handle_sideload_request, ["content-type"])
        self.__http_server.register_endpoint(
            "GET",
            auth_endpoint,
            self.__handle_auth_request,
            ["x-original-length", "x-original-method", "x-original-uri", "hue-whitelist"],
        )
        self.__mqtt = mqtt
        self.__event_sink = event_sink
        self.__last_button_press = None
        self.__options = 0
        self.__last_auth = None
        self.task = self.__mqtt_subscribe_loop()

    async def __aenter__(self):
        # An exception in `__aenter__` causes the program to silently terminate
        # in micropython. Because starting the HTTP server may actually fail,
        # we need to explicitly intercept the exception and log it.
        try:
            await self.__http_server.start()
        except Exception as ex:
            self._logger.error(f"unable to start: {type(ex).__name__}({str(ex)})")
            raise
        await self.__event_sink(
            ComponentEvent(
                command="announce",
                cid=config.bridge_component,
                eid=time_ns(),
                source="sideload",
                version="unknown",
                frontend=self,
            )
        )
        return self

    async def __aexit__(self, *_):
        await self.__http_server.stop()

    def notify(self, options: int):
        if options:
            self._logger.info("Special image notification, options=0x%02X", options)
        elif self.__options:
            self._logger.info("Special options cleared")
        self.__options = options

    async def __handle_options_request(self, *_):
        return Response(status=Response.OK, content_type="text/html", body="", headers=COMMON_RESPONSE_HEADERS)

    async def __handle_device_nanoconfig_request(
        self, server: HttpServer, headers: dict, mac
    ):  # pylint: disable=unused-argument
        if not mac:
            return Response(
                status=Response.NOT_FOUND,
                content_type="text/html",
                body=Response.NOT_FOUND.message,
                headers=COMMON_RESPONSE_HEADERS,
            )
        event = ComponentEvent(
            command="query",
            cid=f"{config.zigbee_component_prefix}{mac.lower()}",
            source="unknown",
            version="unknown",
        )
        await self.__event_sink(event)
        await event.wait_accepted()
        if "error" in event:
            self._logger.warning("Query failed for device, mac=%s, error=%s", mac, event.error)
            return Response(
                status=Response.INTERNAL_SERVER_ERROR,
                content_type="text/html",
                body=event.error,
                headers=COMMON_RESPONSE_HEADERS,
            )
        # Valid MAC in URI, return a device nanoconfig.
        return Response(
            status=Response.OK,
            content_type="application/json",
            body=json.dumps(
                event.remap(
                    "version",
                    "recommended_version",
                    "state",
                    "manufacturer_code",
                    "image_type",
                    "reachable",
                    manufacturer_code=lambda mc: f"{mc:04x}",  # pylint: disable=unnecessary-lambda
                    image_type=lambda it: f"{it:04x}",  # pylint: disable=unnecessary-lambda
                )
            ),
            headers=COMMON_RESPONSE_HEADERS,
        )

    async def __handle_nanoconfig_request(self, server: HttpServer, headers: dict):  # pylint: disable=unused-argument
        nanoconfig = {
            "model_id": hal().get_platform_id(),
            "bridge_id": hal().get_board_id().upper(),
            "software_version": hal().get_version(),
        }
        if components := hal().get_component_versions():
            nanoconfig.update(components=components)
        return Response(
            status=Response.OK,
            content_type="application/json",
            body=json.dumps(nanoconfig),
            headers=COMMON_RESPONSE_HEADERS,
        )

    def __parse_sideload_headers(self, headers: dict) -> tuple:
        BOUNDARY = "boundary="
        multipart, boundary, length = False, None, headers.get("content-length", 0)
        if content_type := headers.get("content-type"):
            for part in content_type.split("; ", 1):
                if part == "multipart/form-data":
                    multipart = True
                if part.startswith(BOUNDARY):
                    # RFC2045, 5.1 Syntax of the Content-Type Header Field
                    # allows quoting of the boundary parameter.
                    boundary = part[len(BOUNDARY) :].strip('"')
        if length and multipart and boundary:
            return int(length), bytes(boundary, "ascii")
        return None

    async def __handle_sideload_request(self, server: HttpServer, headers: dict, mac):
        if metadata := self.__parse_sideload_headers(headers):
            content_length, boundary = metadata
            start_sentinel = b"--" + boundary + b"\r\n"
            end_sentinel = b"\r\n--" + boundary + b"--\r\n"
            if (block := await server.reader.read(1024)).startswith(start_sentinel):
                if (data_start := block.find(b"\r\n\r\n")) != -1:
                    status, body = await self.__handle_component_update(
                        reader=server.reader,
                        seed=block[(data_start + 4) :],
                        end_sentinel=end_sentinel,
                        mac=mac,
                        content_length=content_length,
                    )
                    self._logger.info("Sideload complete, response=%d %s", status.code, body)
                    return Response(
                        status=status,
                        content_type="text/html",
                        body=body,
                        headers=COMMON_RESPONSE_HEADERS,
                    )
                self._logger.warning("Multipart content did not start after scanning 512 bytes")
            else:
                self._logger.warning("Bad body, expected=%s actual=%s", start_sentinel, block[: len(start_sentinel)])
        else:
            self._logger.warning("Unexpected request, headers=%s", headers)
        return Response(
            status=Response.BAD_REQUEST,
            content_type="text/html",
            body="",
            headers={"Connection": "close"},
        )

    async def __handle_component_update(  # noqa
        self, reader, seed: bytes, end_sentinel: bytes, mac: str, content_length: int
    ) -> str:
        if mac:
            return await self.__handle_device_update(reader, seed, end_sentinel, mac, content_length)
        return await self.__handle_bridge_update(reader, seed, end_sentinel)

    def __remap_libflasher_error(self, error_code: int) -> str:
        return {
            SW_ERROR_GROUP_IMAGE_TOO_BIG: "Image too big",
            SW_ERROR_GROUP_IMAGE_INVALID: "Image invalid",
            SW_ERROR_GROUP_IMAGE_INCOMPLETE: "Image incomplete",
            SW_ERROR_GROUP_VERSION_INVALID: "Image version invalid",
        }.get(error_code & SW_ERROR_GROUP_MASK, "Upload failed")

    async def __handle_bridge_update(self, reader, seed: bytes, end_sentinel: bytes) -> tuple:
        event = ComponentEvent(
            command="update",
            cid=config.bridge_component,
            eid=time_ns(),
            source="sideload",
            version="unknown",
            reader=reader,
            seed=seed,
            end_sentinel=end_sentinel,
            mandatory=True,
            auth=self.__last_auth,
        )
        await self.__event_sink(event)
        await event.wait_accepted()
        if "error" in event:
            return Response.OK, self.__remap_libflasher_error(event.get("error_code", 0))
        if event.get("reboot", True):
            return Response.OK, "Upload OK, system will reboot"
        return Response.OK, "Upload OK"

    async def __handle_device_update(  # noqa
        self, reader, seed: bytes, end_sentinel: bytes, mac: str, content_length: int
    ) -> tuple:
        self._logger.info("Will attempt to sideload device, mac=%s", mac)
        file_path = f"{config.fw_repository_path}/{mac}"
        error = None
        try:
            if content_length > config.dynamic["fw_repository_budget"]:
                raise StreamSizeError(config.dynamic["fw_repository_budget"], content_length)
            async with await stream_wrapper_from_reader(reader, seed, end_sentinel) as stream:
                with open(file_path, "wb") as file:
                    spy = StreamSpy(struct.calcsize(OTAU_HEADER_SPEC), file.write)
                    await stream.stream(consumer=spy)
                    magic, version, *_, file_version = struct.unpack(OTAU_HEADER_SPEC, spy.data)
                    self._logger.info(
                        "OTAU header, magic=0x%08X, version=0x%04X, file_version=%d", magic, version, file_version
                    )
                    if magic != OTAU_MAGIC or version != OTAU_HEADER_VERSION:
                        raise Exception("Not a valid OTAU header")
            event = ComponentEvent(
                command="update",
                cid=f"{config.zigbee_component_prefix}{mac.lower()}",
                eid=time_ns(),
                source="sideload",
                version=file_version,
                url=f"file://{file_path}",
                checksum=stream.md5(),
                mandatory=True,
            )
            await self.__event_sink(event)
            await event.wait_accepted()
            error = event.get("error")
        except Exception as ex:
            error = f"{type(ex).__name__}({str(ex)})"
        finally:
            self.__options = 0
        if error:
            unlink_quietly(file_path)
            return Response.INTERNAL_SERVER_ERROR, error
        return Response.OK, "Upload OK, OTA image stored"

    async def __handle_whitelist(self, headers: dict) -> int:
        if hue_whitelist := headers.get("hue-whitelist"):
            try:
                response = await huettp.request(
                    "GET",
                    config.whitelist_auth_endpoint,
                    headers={"hue-application-key": hue_whitelist},
                    timeout=AUTH_TIMEOUT,
                )
                self._logger.info(
                    "Authentication proxied to %s, status=%d", config.whitelist_auth_endpoint, response.status
                )
                return response.status
            except Exception as ex:
                self._logger.warning(
                    "Authentication request to %s failed: %s(%s)",
                    config.whitelist_auth_endpoint,
                    type(ex).__name__,
                    str(ex),
                )
                return 500
        return 403

    async def __handle_auth_request(self, _, headers: dict):
        method, uri = headers["x-original-method"], headers["x-original-uri"]
        content_length = int(headers.get("x-original-length", 0))
        pressed = time() - self.__last_button_press if self.__last_button_press else None
        pressed_text = f"pressed {pretty_interval(pressed)} ago" if pressed else "never pressed"
        device = bool(re.match(config.sideload_endpoint, headers["x-original-uri"]).groups()[0])
        self._logger.info(
            "Authenticating %s %s, content-length=%d, options=0x%02X, link button %s",
            method,
            uri,
            content_length,
            self.__options,
            pressed_text,
        )

        # GET or OPTIONS are always and unconditionally allowed.
        if method in ("GET", "OPTIONS"):
            self._logger.info("Authenticated")
            return Response(status=Response.OK, content_type="text/html", body=Response.OK.message)

        # (Likely) special images are allowed, but only on the main endpoint.
        if not device and content_length <= SNEAKY_IMAGE_SIZE:
            self._logger.info("Authenticated")
            self.__last_auth = "sneaky"
            return Response(status=Response.OK, content_type="text/html", body=Response.OK.message)

        # Special image with "No Whitelist" flag was uploaded previously.
        if self.__options & FW2_DONT_REQUIRE_WHITELIST:
            self._logger.info("Authenticated")
            self.__last_auth = "nowhitelist"
            return Response(status=Response.OK, content_type="text/html", body=Response.OK.message)

        # Whitelist handling, but only on the main endpoint.
        if not device:
            # Authentication sub-request failed, check the link button.
            if self.__options & AUTH_ALLOW_BUTTON_WHITELIST_BYPASS and pressed and pressed <= LINK_BUTTON_WINDOW:
                self._logger.info("Authenticated")
                self.__last_auth = "button"
                return Response(status=Response.OK, content_type="text/html", body=Response.OK.message)

            # Attempt to authenticate the whitelist entry.
            authorisation_response = await self.__handle_whitelist(headers) // 100
            if authorisation_response == 2:
                self._logger.info("Authenticated")
                self.__last_auth = "whitelist"
                return Response(status=Response.OK, content_type="text/html", body=Response.OK.message)

            if authorisation_response == 5:
                self._logger.warning("Authentication provider unreachable, will allow bypass")
                self.__options = AUTH_ALLOW_BUTTON_WHITELIST_BYPASS
                self.__last_auth = None
                return Response(
                    status=Response.I_AM_A_TEAPOT, content_type="text/html", body=Response.I_AM_A_TEAPOT.message
                )

        self._logger.info("NOT authenticated")
        self.__last_auth = None
        self.__options = 0
        return Response(status=Response.FORBIDDEN, content_type="text/html", body="Not authorized")

    async def __mqtt_subscribe_loop(self):
        self._logger.info("Awaiting for link button events")
        async for message in self.__mqtt.subscribe("button/link"):
            try:
                if message["payload"] == b"pressed":
                    self._logger.info("Link button pressed")
                    self.__last_button_press = time()
            except MqttError:
                raise
            except Exception:
                self._logger.exception("Error in the MQTT subscribe loop")
