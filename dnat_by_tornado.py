import socket
import errno
import tornado.ioloop


buffer_size = 2048
forward_addr = ('192.168.199.1', 80)


class Forward(object):
    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except socket.error as e:
            print e.errno
            return False


class Server(object):
    table = {}

    def __init__(self, sock, client, client_addr):
        self.server = sock
        self.client = client
        self.client_addr = client_addr

    def on_accept(self):
        forward = Forward().start(*forward_addr)
        if forward:
            print "%s has connected %s" % (self.client_addr, forward.getpeername())
            self.table[self.client] = forward
            self.table[forward] = self.client
            self.client = self.client
        else:
            print 'Cannot establish conn with remote server.'
            print 'Closing conn with client %s', self.client_addr
            self.client.close()

    def on_close(self):
        print '%s:%s has disconnected' % self.client.getpeername()
        out = self.table[self.client]
        self.table[out].close()
        self.table[self.client].close()
        del self.table[out], self.table[self.client]

    def on_recv(self, data):
        print 'data:', data
        self.table[self.client].send(data)

    @staticmethod
    def connection_ready(sock, events):
        while True:
            try:
                conn, address = sock.accept()
            except socket.error as e:
                if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise
                return
            conn.setblocking(0)

            server = Server(sock, conn, address)
            server.on_accept()
            try:
                data = server.client.recv(buffer_size)
            except socket.error as e:
                if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise

            if len(data) == 0:
                server.on_close()
            else:
                server.on_recv(data)


def start_listen_socket(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 9527))
    sock.listen(128)
    return sock

if __name__ == '__main__':
    sock = start_listen_socket('', 9527)
    io_loop = tornado.ioloop.IOLoop.current()
    io_loop.add_handler(sock, Server.connection_ready, io_loop.READ)
    io_loop.start()
