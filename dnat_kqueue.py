import socket
import select
import sys

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

    def __init__(self, host, port):
        self.client = None
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(128)

    @property
    def kq_event(self):
        return [select.kevent(
            self.server.fileno(),
            filter=select.KQ_FILTER_READ,
            flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR,
        )]

    def main_loop(self):
        kq = select.kqueue()
        kq.control(self.kq_event, 0, 0)
        r_events = kq.control(None, 1)
        while True:
            for _ in r_events:
                self.on_accept()
                data = self.client.recv(buffer_size)

                if len(data) == 0:
                    self.on_close()
                else:
                    self.on_recv(data)

    def on_accept(self):
        forward = Forward().start(*forward_addr)
        client_sock, client_addr = self.server.accept()
        if forward:
            print "%s has connected %s" % (client_addr, forward.getpeername())
            self.table[client_sock] = forward
            self.table[forward] = client_sock
            self.client = client_sock
        else:
            print 'Cannot establish connection with remote server.'
            print 'Closing connection with client %s', client_addr
            client_sock.close()

    def on_close(self):
        print '%s has disconnected', self.client.getpeername()
        out = self.table[self.client]
        self.table[out].close()
        # close the connection with remote server
        self.table[self.client].close()
        del self.table[out], self.table[self.client]

    def on_recv(self, data):
        # handle data before send forward
        print 'data:', data
        self.table[self.client].send(data)


if __name__ == '__main__':
    server = Server('', 9527)
    try:
        server.main_loop()
    except KeyboardInterrupt:
        print "Ctrl C - Stopping server"
        sys.exit(1)
