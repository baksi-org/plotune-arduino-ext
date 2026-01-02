from plotune_sdk import FormLayout
from serial.tools import list_ports


def discover_serial_ports():
    return [p.device for p in list_ports.comports()] or ["AUTO"]


def dynamic_arduino_form():
    form = FormLayout()

    # =========================
    # Connection
    # =========================
    form.add_tab("Connection").add_combobox(
        "serial_port",
        "Serial Port",
        ["AUTO"] + discover_serial_ports(),
        default="AUTO",
        required=True,
    ).add_combobox(
        "baudrate",
        "Baudrate",
        ["300", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"],
        default="115200",
        required=True,
    )

    # =========================
    # Line Format
    # =========================
    form.add_tab("Format: Line").add_checkbox(
        "line_enable", "Enable Line Format", default=True
    ).add_text("line_key", "Signal Key", default="arduino")

    # =========================
    # CSV Format
    # =========================
    form.add_tab("Format: CSV").add_checkbox(
        "csv_enable", "Enable CSV Format", default=False
    ).add_text("csv_delimiter", "Delimiter", default=",").add_text(
        "csv_key_index", "Key Index", default="0"
    ).add_text(
        "csv_value_index", "Value Index", default="1"
    ).add_text(
        "csv_time_index", "Time Index (optional)", default=""
    )

    # =========================
    # JSON Format
    # =========================
    form.add_tab("Format: JSON").add_checkbox(
        "json_enable", "Enable JSON Format", default=False
    ).add_text("json_key_field", "Key Field", default="key").add_text(
        "json_value_field", "Value Field", default="value"
    ).add_text(
        "json_time_field", "Time Field (optional)", default="time"
    )

    # =========================
    # Actions
    # =========================
    from core.utils.constant_helper import get_config

    conf = get_config().get("connection", {})
    url = f"http://{conf.get('ip','127.0.0.1')}:{conf.get('port','')}"

    form.add_group("Actions").add_button(
        "connect",
        "Connect Arduino",
        {
            "method": "POST",
            "url": f"{url}/connect",
            "payload_fields": ["serial_port", "baudrate"],
        },
    )

    return form.to_schema()


from core.models.form_input import FormInput
from uuid import uuid4


def form_dict_to_input(data: dict) -> FormInput:
    line_key = data.get("line_key") or uuid4().hex[:6]

    def safe_int(val, default=None):
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    return FormInput(
        serial_port=data.get("serial_port", "AUTO"),
        baudrate=safe_int(data.get("baudrate"), 115200),
        line_enable=bool(data.get("line_enable", True)),
        line_key=line_key,
        csv_enable=bool(data.get("csv_enable", False)),
        csv_delimiter=data.get("csv_delimiter", ","),
        csv_key_index=safe_int(data.get("csv_key_index"), 0),
        csv_value_index=safe_int(data.get("csv_value_index"), 1),
        csv_time_index=safe_int(data.get("csv_time_index"), None),
        json_enable=bool(data.get("json_enable", False)),
        json_key_field=data.get("json_key_field", "key"),
        json_value_field=data.get("json_value_field", "value"),
        json_time_field=data.get("json_time_field", "time"),
    )
