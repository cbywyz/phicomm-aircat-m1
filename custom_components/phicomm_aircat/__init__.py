"""斐讯悟空 M1 空气检测器本地接管集成。

通过 DNS 劫持 aircat.phicomm.com -> 本机，监听 TCP 9000 接收设备私有协议帧，
正确回 ACK 后设备持续上报温湿度/PM2.5/甲醛，解析后输出为 HA 传感器实体。
参考协议：daniel_st 逆向 + corbamico/phicomm-aircat-srv。
"""

import asyncio
import json
import logging
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PORT, END_MARK, HEARTBEAT_ACK

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


class AirCatServer:
    """TCP 服务器，接收悟空 M1 上报并解析。"""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.server = None
        self.entities = []
        self.data = {
            "temperature": None,
            "humidity": None,
            "pm25": None,
            "hcho": None,
            "last_seen": None,
        }

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, "0.0.0.0", PORT
        )
        _LOGGER.info("AirCat TCP server listening on %s", PORT)

    async def stop(self):
        if self.server:
            self.server.close()
            try:
                await self.server.wait_closed()
            except Exception:  # noqa
                pass

    async def handle_client(self, reader, writer):
        try:
            while True:
                data = await reader.read(2048)
                if not data:
                    break
                await self.process(data, writer)
        except Exception as e:  # noqa
            _LOGGER.debug("AirCat client error: %s", e)
        finally:
            try:
                writer.close()
            except Exception:  # noqa
                pass

    async def process(self, data: bytes, writer):
        if END_MARK not in data:
            return
        # 1) 回 ACK（取前 23 字节设备头），激发设备上报
        if len(data) >= 23:
            try:
                writer.write(data[:23] + HEARTBEAT_ACK)
                await writer.drain()
            except Exception:  # noqa
                pass
        # 2) 解析数据帧（直接在原始字节里定位 JSON，避免 \xff 被 UTF-8 解码丢弃）
        if not (b'"humidity"' in data or b'"value"' in data or b'"temperature"' in data):
            return
        try:
            start = data.find(b"{")
            end = data.find(b"}\xff#END#")
            if start < 0 or end <= start:
                return
            raw = data[start : end + 1]  # 含结尾的 }
            obj = json.loads(raw)
        except Exception:  # noqa
            return
        changed = False
        for key, src in (
            ("temperature", "temperature"),
            ("humidity", "humidity"),
            ("pm25", "value"),
            ("hcho", "hcho"),
        ):
            val = obj.get(src)
            if val is not None:
                try:
                    self.data[key] = float(val)
                    changed = True
                except (TypeError, ValueError):
                    pass
        if changed:
            self.data["last_seen"] = datetime.now()
            self._schedule_update()

    def _schedule_update(self):
        self.hass.loop.call_soon_threadsafe(self._update_entities)

    def _update_entities(self):
        for ent in self.entities:
            ent.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    server = AirCatServer(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = server
    await server.start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(server.stop)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    server = hass.data[DOMAIN].pop(entry.entry_id, None)
    if server:
        await server.stop()
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return True
