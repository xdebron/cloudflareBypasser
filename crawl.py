from urllib.parse import urlparse
import time
import threading
import socket
import queue
import optparse
import struct
import ssl


class iprangescanner():
    def __init__(self, url, inputfile, threadcount, searchstr):

        self.url = url
        self.inputfile = inputfile
        self.threadcount = threadcount
        self.searchstr = searchstr

        self.isssl, self.port, self.url, self.host = self.parse_url()
        self.headers = self.create_headers()

        self.q = queue.Queue()

        self.main()

    def ip2long(self, ip):
        return struct.unpack("!L", socket.inet_aton(ip))[0]

    def long2ip(self, long):
        return socket.inet_ntoa(struct.pack('!L', long))

    def parse_line(self, line):
        if "/" in line:
            data = line.strip().split("/")
            start = self.ip2long(data[0])
            return [self.long2ip(start + x) for x in
                range(0, 2**(32 - int(data[1])))]
        elif "-" in line:
            data = list(map(self.ip2long, line.strip().split("-")))
            return [self.long2ip(x) for x in
                range(min(data), max(data))]
        else:
            return [line.strip()]

    def decode(self, s):
        encodings = ('ascii', 'utf8', 'latin1')
        for encoding in encodings:
            try:
                return s.decode(encoding)
            except UnicodeDecodeError:
                pass
        return s.decode('ascii', 'ignore')

    def parse_url(self):
        parsed = urlparse(self.url)
        print(parsed)

        if parsed.scheme == "https":
            isssl = True
            port = 443
        else:
            isssl = False
            port = 80

        if parsed.query == "":
            url = parsed.path
        else:
            url = "{0}?{1}".format(parsed.path, parsed.query)

        return isssl, port, url, parsed.netloc

    def create_headers(self):
        headers = "GET {0} HTTP/1.0\r\n".format(self.url) + \
                  "Host: {0}\r\n".format(self.host) + \
                  "Connection: close\r\n" + \
                  "Accept-Encoding: None\r\n" + \
                  "User-Agent: Mozilla/5.0\r\n\r\n"
        return headers.encode("ascii")

    def read_socket(self, sock):
        doc = bytearray()
        buf = sock.recv(1024)
        while buf:
            doc += buf
            buf = sock.recv(1024)
        return self.decode(doc)

    def worker(self):
        while not self.q.empty():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ip = self.q.get()
            try:
                s.settimeout(5.0)
                s.connect((ip, self.port))
                if self.isssl:
                    s = ssl.wrap_socket(s)
                s.send(self.headers)
                html = self.read_socket(s)
                if self.searchstr in html and "cf-ray:" not in html:
                    open("output.txt", "a").write("{0}\n".format(ip))

            except:
                pass
            s.close()

    def main(self):
        with open(self.inputfile, "r") as file:
            lines = file.readlines()
            for line in lines:
                iplist = self.parse_line(line)
                for ip in iplist:
                    #print(ip)
                    self.q.put(str(ip))

        self.queue_len = self.q.qsize()
        print("QUEUE LEN: {0}".format(self.queue_len))

        for i in range(0, self.threadcount):
            threading.Thread(target=self.worker, args=()).start()

if __name__ == "__main__":

    parser = optparse.OptionParser(usage="%prog --find=\"search\" --url=\"http://www.google.com/?asdasd=asd\" --ip-list=\"iplist.txt\"")

    parser.add_option('-t', '--thread', dest="THREAD_COUNT", type="int",
                      action="store", help="Thread count. (1024)", default=1024)

    parser.add_option('-f', '--find', dest="SEARCH_STR", type="str",
                      action="store", help="Search for a string in website.")

    parser.add_option('-u', '--url', dest="WEB_URL", type="str",
                      action="store", help="Url of website")

    parser.add_option('-i', '--ip-list', dest="IPLIST_FILE", type="str",
                      action="store", help="Suspected ip list. CIDR, IP-range and IP list are all valid.", default="iplist.txt")

    (options, args) = parser.parse_args()

    scanner = iprangescanner(options.WEB_URL, options.IPLIST_FILE, options.THREAD_COUNT, options.SEARCH_STR)

    while not scanner.q.empty():
        print(scanner.q.qsize())
        time.sleep(1)
