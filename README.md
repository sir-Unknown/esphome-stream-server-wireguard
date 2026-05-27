Stream server for ESPHome (fork)
=================================

> **This is a fork of [oxan/esphome-stream-server](https://github.com/oxan/esphome-stream-server).**
>
> Added functionality:
> - **`bind_wg`** — optional config option that binds the TCP server exclusively to a WireGuard interface IP, so the port is only reachable through the VPN tunnel. When omitted, behaviour is identical to the upstream component (binds to `0.0.0.0`). If the WireGuard interface is not yet up at boot, binding is retried automatically each loop iteration until it succeeds.

Custom component for ESPHome to expose a UART stream over WiFi or Ethernet. Provides a serial-to-wifi bridge as known
from ESPLink or ser2net, using ESPHome.

This component creates a TCP server listening on port 6638 (by default), and relays all data between the connected
clients and the serial port. It doesn't support any control sequences, telnet options or RFC 2217, just raw data.

Usage
-----

Requires ESPHome v2022.3.0 or newer.

```yaml
external_components:
  - source: github://oxan/esphome-stream-server

stream_server:
```

You can set the UART ID and port to be used under the `stream_server` component.

```yaml
uart:
   id: uart_bus
   # add further configuration for the UART here

stream_server:
   uart_id: uart_bus
   port: 1234
```

Sensors
-------
The server provides a binary sensor that signals whether there currently is a client connected:

```yaml
binary_sensor:
  - platform: stream_server
    connected:
      name: Connected
```

It also provides a numeric sensor that indicates the number of connected clients:

```yaml
sensor:
  - platform: stream_server
    connection_count:
      name: Number of connections
```

Advanced
--------
It is possible to define multiple stream servers for multiple UARTs simultaneously:

```yaml
uart:
  - id: uart1
    # ...
  - id: uart2
    # ...

stream_server:
  - uart_id: uart1
    port: 1234
  - uart_id: uart2
    port: 1235
```

The stream server has an internal buffer into which UART data is read before it is transmitted over TCP. The size of
this buffer can be changed using the `buffer_size` option, and must be a power of two. Increasing the buffer size above
the default of 128 bytes can help to achieve optimal throughput, and is especially helpful when using high baudrates. It
can also be necessary to increase the [`rx_buffer_size`][uart-config] option of the UART itself.

```yaml
stream_server:
    buffer_size: 2048
```

[uart-config]: https://esphome.io/components/uart.html#configuration-variables

WireGuard binding
-----------------

Use `bind_wg` to restrict the TCP server to a WireGuard interface. The port will only be reachable through the VPN
tunnel — connections from the regular WiFi/Ethernet interface are not accepted.

```yaml
external_components:
  - source: github://sir-Unknown/esphome-stream-server

wireguard:
  id: my_wg
  address: 172.27.66.2
  # ... rest of WireGuard configuration

stream_server:
  uart_id: uart_bus
  port: 7638
  bind_wg: my_wg
```

If the WireGuard interface is not yet up when the device boots, the stream server will keep retrying in the background
until the bind succeeds. No manual intervention or reboot is needed. Omitting `bind_wg` restores the default behaviour
of binding to `0.0.0.0` (all interfaces).
