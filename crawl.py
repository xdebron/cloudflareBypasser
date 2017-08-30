# -*- coding: utf-8 -*-
import time,threading,socket,Queue,optparse,sys,struct
from urlparse import urlparse

parser = optparse.OptionParser(usage="%prog --ara=\"arama\" --url=\"http://www.google.com/?asdasd=asd\" --ip-list=\"iplist.txt\"\n\nOrnek:	%prog --ara=\"netiyi\" --url=\"http://www.sabotaj.net/\" --ip-list=\"iplist.txt\"")
parser.add_option('-t', '--thread', dest="THREAD_COUNT",type="int",
				  action="store",help="Thread sayisi. Varsayilan: 1024", default=1024)
parser.add_option('-a', '--ara', dest="ARANACAK_STR",type="str",
				  action="store",help="Websitesinde gecen bir cumle veya kelime.")
parser.add_option('-u', '--url', dest="WEB_URL",type="str",
				  action="store",help="Cumle veya kelimenin gectigi sayfa urlsi.")
parser.add_option('-i', '--ip-list', dest="IPLIST_FILE",type="str",
				  action="store",help="Suphelendiginiz iplerin listesi. CIDR veya IP listesi.")

(options, args) = parser.parse_args()

if len(sys.argv) < 4:
	parser.print_help()
	sys.exit(1)

def parse_line(line):
	if "/" in line:
		data=line.strip().split("/")
		start=struct.unpack("!L", socket.inet_aton(data[0]))[0]
		return [socket.inet_ntoa(struct.pack('!L', start+x)) for x in xrange(0,2**(32-int(data[1])))]
	else:
		return [line.strip()]

print "{0} Thread.".format(options.THREAD_COUNT)
if not options.WEB_URL:
	parser.error('Url girmelisiniz.')
parsed=urlparse(options.WEB_URL)
if parsed.scheme=="https":
	parser.error('Simdilik ssl desteklemiyoruz.')
elif parsed.scheme!="http":
	parser.error('Dogru url girdiginize emin olun.')

if not options.ARANACAK_STR:
	parser.error('Aranacak kelime girmelisiniz.')


if parsed.query != "":
	url = "{0}?{1}".format(parsed.path, parsed.query)
else:
	url = parsed.path
IP_LIST_FILE= open(options.IPLIST_FILE,"r").readlines()
HEADERS= "GET {0} HTTP/1.1\r\nHost: {1}\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n".format(url,parsed.netloc)
q=Queue.Queue()
for line in IP_LIST_FILE:
	IP_LIST = parse_line(line)
	for ip in IP_LIST:
		q.put(str(ip))
IP_LIST_FILE=None
QUEUE_LEN=q.qsize()

print "{0} ip taranacak.".format(QUEUE_LEN)



def socket_oku(sock):
	doc=""
	buf = sock.recv(1024)
	while buf:
		doc+=buf
		buf = sock.recv(1024)
	return doc

def worker():
	while not q.empty():
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		ip=q.get()
		try:
			s.connect((ip, 80))
			s.settimeout(5.0)
			s.send(HEADERS)
			html=socket_oku(s)
			if options.ARANACAK_STR in html:
				print ip
				open("bulundu.txt","a").write("{0}\n".format(ip))
		except:
			None
		s.close()

for i in xrange(0,options.THREAD_COUNT):
	try:
		threading.Thread( target=worker, args=() ).start()
	except:
		print "{0}. thread acilamadi."
while True:
	new_size=q.qsize()
	if not new_size==0:
		print "{1}/{0}".format(QUEUE_LEN, QUEUE_LEN - new_size)
		time.sleep(1)
	else:
		break

