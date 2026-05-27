import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import uart
from esphome.const import CONF_ADDRESS, CONF_ID, CONF_PORT, CONF_BUFFER_SIZE
from esphome.util import parse_esphome_version

# ESPHome doesn't know the Stream abstraction yet, so hardcode to use a UART for now.

AUTO_LOAD = ["socket"]

DEPENDENCIES = ["uart", "network"]

MULTI_CONF = True

CONF_BIND_WG = "bind_wg"

ns = cg.global_ns
StreamServerComponent = ns.class_("StreamServerComponent", cg.Component)


def validate_buffer_size(buffer_size):
    if buffer_size & (buffer_size - 1) != 0:
        raise cv.Invalid("Buffer size must be a power of two.")
    return buffer_size


def _wireguard_id_schema(value):
    from esphome.components.wireguard import Wireguard  # noqa: PLC0415
    return cv.use_id(Wireguard)(value)


CONFIG_SCHEMA = cv.All(
    cv.require_esphome_version(2022, 3, 0),
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(StreamServerComponent),
            cv.Optional(CONF_PORT, default=6638): cv.port,
            cv.Optional(CONF_BUFFER_SIZE, default=128): cv.All(
                cv.positive_int, validate_buffer_size
            ),
            cv.Optional(CONF_BIND_WG): _wireguard_id_schema,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA),
)


def _get_wireguard_address(wg_id):
    """Return the address string configured on the WireGuard component with the given ID."""
    from esphome.core import CORE  # noqa: PLC0415
    wg_config = CORE.config.get("wireguard")
    if wg_config is None:
        raise cv.Invalid("No wireguard component found in config")
    # WireGuard is not MULTI_CONF so the config is a single dict.
    entries = wg_config if isinstance(wg_config, list) else [wg_config]
    for entry in entries:
        if entry.get(CONF_ID) == wg_id:
            return str(entry[CONF_ADDRESS])
    raise cv.Invalid(f"Could not find wireguard component with id '{wg_id}' to resolve bind address")


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    cg.add(var.set_port(config[CONF_PORT]))
    cg.add(var.set_buffer_size(config[CONF_BUFFER_SIZE]))

    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)

    if CONF_BIND_WG in config:
        wg_id = config[CONF_BIND_WG]
        wg_var = await cg.get_variable(wg_id)
        bind_address = _get_wireguard_address(wg_id)
        cg.add(var.set_bind_wg(wg_var, bind_address))

    esphome_version = parse_esphome_version()
    if (2025, 12, 0) <= esphome_version < (2026, 3, 0):
        uart.request_wake_loop_on_rx()
