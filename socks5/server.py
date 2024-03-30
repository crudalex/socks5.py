import asyncio
import socket
from struct import pack, unpack
from socks5.client import Client
import logging


class Server(asyncio.Protocol):
    INIT, HOST, DATA = 0, 1, 2

    def __init__(self, timeout):
        self.timeout = timeout
        self.transport = None
        self.client_transport = None
        self.state = None

    def connection_made(self, transport):
        peername = transport.get_extra_info("peername")
        logging.debug("Connection from: %s", peername)
        self.transport = transport
        self.state = self.INIT

    def connection_lost(self, exc):
        self.transport.close()
        logging.debug("Server connection lost.")

    def data_received(self, data):
        logging.debug("Received data from client: %s", data)
        if self.state == self.INIT:
            assert data[0] == 0x05
            self.transport.write(pack("!BB", 0x05, 0x00))  # no auth
            self.state = self.HOST
            logging.debug("Sent no-auth response to client.")

        elif self.state == self.HOST:
            ver, cmd, _, atype = data[:4]
            assert ver == 0x05 and cmd == 0x01

            if atype == 3:  # domain
                length = data[4]
                hostname, nxt = data[5 : 5 + length], 5 + length
            elif atype == 1:  # ipv4
                hostname, nxt = socket.inet_ntop(socket.AF_INET, data[4:8]), 8
            elif atype == 4:  # ipv6
                hostname, nxt = socket.inet_ntop(socket.AF_INET6, data[4:20]), 20
            port = unpack("!H", data[nxt : nxt + 2])[0]

            logging.debug("Target: %s:%s", hostname, port)
            asyncio.ensure_future(self.connect(hostname, port))
            self.state = self.DATA

        elif self.state == self.DATA:
            self.client_transport.write(data)
            logging.debug("Forwarded data to target server.")

    async def connect(self, hostname, port):
        try:
            loop = asyncio.get_event_loop()
            transport, client = await asyncio.wait_for(
                loop.create_connection(Client, hostname, port), timeout=self.timeout
            )
            client.server_transport = self.transport
            self.client_transport = transport

            hostip, port = transport.get_extra_info("sockname")
            host = unpack("!I", socket.inet_aton(hostip))[0]
            response = pack("!BBBBIH", 0x05, 0x00, 0x00, 0x01, host, port)
            self.transport.write(response)
            logging.debug("Sent connection established response to client.")

        except asyncio.TimeoutError:
            logging.error("Connection to %s:%s timed out", hostname, port)
            self.transport.close()

        except OSError:
            logging.error("Failed to connect to %s:%s", hostname, port)
            self.transport.close()


async def run_proxy_server(listen_address, listen_port, timeout):
    loop = asyncio.get_event_loop()

    coro = loop.create_server(
        lambda: Server(timeout=timeout), listen_address, listen_port
    )
    server = await asyncio.wait_for(coro, timeout=timeout)

    logging.info("Server listening on %s:%s...", listen_address, listen_port)
    logging.info("Timeout: %s seconds", timeout)

    try:
        await server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.close()
    await server.wait_closed()
    loop.close()
