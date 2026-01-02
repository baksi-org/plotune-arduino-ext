import asyncio
import json
import time
from typing import Optional, Dict, Any
from uuid import uuid4

import serial
from serial.tools import list_ports

from core.models.form_input import FormInput


class SerialManager:
    def __init__(
        self,
        _id: Optional[str] = None,
        form: Optional[FormInput] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self._id = _id or uuid4().hex
        self.form = form or FormInput()
        self.port = self._resolve_port(self.form.serial_port)
        self.baudrate = int(self.form.baudrate)
        self.loop = loop or asyncio.get_event_loop()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.error_queue: asyncio.Queue = asyncio.Queue()
        self._stop_event = asyncio.Event()
        self._reader_task: Optional[asyncio.Task] = None
        self.ser: Optional[serial.Serial] = None

    @staticmethod
    def _resolve_port(port_choice: str) -> str:
        if port_choice and port_choice.upper() != "AUTO":
            return port_choice
        ports = [p.device for p in list_ports.comports()]
        return ports[0] if ports else port_choice

    @staticmethod
    def _to_float(val: Any) -> Optional[float]:
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_index(idx: Optional[int]) -> Optional[int]:
        if idx is None:
            return None
        try:
            return int(idx)
        except (TypeError, ValueError):
            return None

    async def start(self) -> None:
        self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
        self._reader_task = self.loop.create_task(self._read_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._reader_task:
            await self._reader_task
        if self.ser and self.ser.is_open:
            self.ser.close()

    async def _read_loop(self) -> None:
        csv_delim = self.form.csv_delimiter or ","
        csv_key_idx = self._safe_index(self.form.csv_key_index)
        csv_val_idx = self._safe_index(self.form.csv_value_index)
        csv_time_idx = self._safe_index(self.form.csv_time_index)

        json_key_field = self.form.json_key_field or "key"
        json_value_field = self.form.json_value_field or "value"
        json_time_field = self.form.json_time_field or "time"

        line_key = self.form.line_key or uuid4().hex[:6]

        while not self._stop_event.is_set():
            if not self.ser or not self.ser.in_waiting:
                await asyncio.sleep(0.01)
                continue

            try:
                raw = self.ser.readline().decode(errors="ignore").strip()
            except Exception as exc:
                await self.error_queue.put({"type": "serial_error", "error": str(exc)})
                await asyncio.sleep(0.01)
                continue

            if not raw:
                await asyncio.sleep(0.01)
                continue

            parsed = None
            err: Optional[Dict[str, Any]] = None

            if self.form.json_enable:
                try:
                    j = json.loads(raw)
                    key = j.get(json_key_field)
                    value = self._to_float(j.get(json_value_field))
                    ts = j.get(json_time_field)
                    ts_f = self._to_float(ts) if ts is not None else None
                    if key is None or value is None:
                        err = {"type": "json_missing_fields", "line": raw}
                    else:
                        parsed = {
                            "key": str(key),
                            "value": float(value),
                            "time": float(ts_f) if ts_f is not None else time.time(),
                        }
                except json.JSONDecodeError as jde:
                    err = {"type": "json_decode_error", "line": raw, "error": str(jde)}

            if parsed is None and self.form.csv_enable:
                parts = raw.split(csv_delim)
                if csv_val_idx is None or csv_val_idx >= len(parts):
                    err = {"type": "csv_value_index_error", "line": raw}
                else:
                    key_part = (
                        parts[csv_key_idx].strip()
                        if csv_key_idx is not None and csv_key_idx < len(parts)
                        else line_key
                    )
                    val_part = parts[csv_val_idx].strip()
                    ts_part = (
                        parts[csv_time_idx].strip()
                        if csv_time_idx is not None and csv_time_idx < len(parts)
                        else None
                    )
                    val_f = self._to_float(val_part)
                    ts_f = self._to_float(ts_part) if ts_part is not None else None
                    if val_f is None:
                        err = {"type": "csv_value_parse_error", "line": raw}
                    else:
                        parsed = {
                            "key": str(key_part),
                            "value": float(val_f),
                            "time": float(ts_f) if ts_f is not None else time.time(),
                        }

            if parsed is None and self.form.line_enable:
                val_f = self._to_float(raw)
                if val_f is None:
                    err = {"type": "line_value_parse_error", "line": raw}
                else:
                    parsed = {
                        "key": line_key,
                        "value": float(val_f),
                        "time": time.time(),
                    }

            if parsed is not None:
                await self.queue.put(parsed)
            else:
                await self.error_queue.put(
                    err or {"type": "unknown_parse_error", "line": raw}
                )

            await asyncio.sleep(0.01)
