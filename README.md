Stream server for ESPHome — with WireGuard binding
===================================================

Fork of [oxan/esphome-stream-server](https://github.com/oxan/esphome-stream-server) that adds
**`bind_wg`**: an optional config option that restricts the TCP server to a WireGuard interface,
so the serial port is only reachable through the VPN tunnel and not exposed on WiFi or Ethernet.
See [WireGuard binding](#wireguard-binding) for configuration and Home Assistant add-on integration.

-----

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
  - source: github://sir-Unknown/esphome-stream-server-wireguard

wireguard:
  id: my_wg
  address: 172.27.66.2
  # ... rest of WireGuard configuration

stream_server:
  uart_id: uart_bus
  port: 7638
  bind_wg: my_wg
```

It also works with multiple stream servers — each one can independently use `bind_wg` or not:

```yaml
stream_server:
  - uart_id: uart1
    port: 1234
    bind_wg: my_wg   # only reachable via VPN

  - uart_id: uart2
    port: 1235        # reachable on all interfaces
```

If the WireGuard interface is not yet up when the device boots, the stream server will keep retrying in the background
until the bind succeeds. No manual intervention or reboot is needed. Omitting `bind_wg` restores the default behaviour
of binding to `0.0.0.0` (all interfaces).

### Using bind_wg with Home Assistant add-ons (OTBR, Zigbee2MQTT)

When `bind_wg` is active the stream server only accepts connections that arrive through the
WireGuard tunnel. Most Home Assistant add-ons run with `host_network: false`, which means their
`wg0` interface exists only inside the WireGuard add-on container and is not reachable from other
add-ons directly.

The solution is to add DNAT rules to the WireGuard add-on so it proxies TCP connections from the
hassio bridge through `wg0` to the ESP32:

```
OTBR / Z2M  →  hassio bridge  →  WireGuard add-on  →  wg0  →  tunnel  →  ESP32
```

**1. Find the WireGuard add-on's hassio IP**

```bash
ha addons info a0d7b954_wireguard | grep ip_address
```

**2. Add iptables rules to the WireGuard add-on**

Add one `PREROUTING` line per port. The `MASQUERADE -o %i` rule is required so the ESP32 sees
the packet as coming from a WireGuard peer IP it can route back through the tunnel, rather than
a hassio bridge address.

```yaml
server:
  post_up: >-
    iptables -A FORWARD -i %i -j ACCEPT;
    iptables -A FORWARD -o %i -j ACCEPT;
    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE;
    iptables -t nat -A POSTROUTING -o %i -j MASQUERADE;
    iptables -t nat -A PREROUTING -p tcp --dport 6638 -j DNAT --to-destination <ESP32_WG_IP>:6638;
    iptables -t nat -A PREROUTING -p tcp --dport 7638 -j DNAT --to-destination <ESP32_WG_IP>:7638
  post_down: >-
    iptables -D FORWARD -i %i -j ACCEPT;
    iptables -D FORWARD -o %i -j ACCEPT;
    iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE;
    iptables -t nat -D POSTROUTING -o %i -j MASQUERADE;
    iptables -t nat -D PREROUTING -p tcp --dport 6638 -j DNAT --to-destination <ESP32_WG_IP>:6638;
    iptables -t nat -D PREROUTING -p tcp --dport 7638 -j DNAT --to-destination <ESP32_WG_IP>:7638
```

**3. OTBR add-on**

OTBR runs with `host_network: true` and reaches the WireGuard add-on via the host's route to the
hassio bridge.

```yaml
network_device: <WG_ADDON_HASSIO_IP>:6638
backbone_interface: <LAN_INTERFACE>
```

**4. Zigbee2MQTT**

Z2M runs with `host_network: false` but shares the hassio bridge with the WireGuard add-on, so it
can reach it directly.

```yaml
serial:
  port: tcp://<WG_ADDON_HASSIO_IP>:7638
```

**5. Restart order**

1. WireGuard add-on — applies the iptables rules
2. OTBR and/or Zigbee2MQTT
