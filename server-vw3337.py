om socket import *
import re
import os
from datetime import datetime, timedelta
import time
import sys

serverPort = int(sys.argv[1])

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(1)
html_strings = ["html", "htm"]
jpg_strings = ["jpeg", "jpg"]
allowed_extensions = [".jpg", ".jpeg", ".html", ".htm", ".txt"]
crlf = "\r\n"

def run():
	while 1:
		try:
			connectionSocket, addr = serverSocket.accept()
			sentence = connectionSocket.recv(2048)
			txtsentence = sentence.decode()

			if not len(txtsentence) == 0:
				items = txtsentence.split("\r\n")
				request = items[0]
				request_items = request.split(" ")
				if check_request_line(request_items, connectionSocket) and find_header(items, connectionSocket):
					requested_item = request_items[1]
					if requested_item[0] == '/':
						requested_item = requested_item[1:]
					data = load_file(requested_item)
					if data:
						size = os.path.getsize(requested_item)
						content_type = get_content_type(requested_item)
						last_modified = os.path.getmtime(requested_item)
						last_modified_date = datetime.fromtimestamp(last_modified) + timedelta(hours=5)
						conditional = handle_conditionals(items)
						new_send = True;
						if conditional:
							date_object = datetime.strptime(conditional, '%a, %d %b %Y %H:%M:%S')
							if date_object >= last_modified_date:
								new_send = False
						if new_send:
							send_headers(connectionSocket, size, content_type, last_modified_date)
							send_file(data, connectionSocket)
						else:
							send_cond_headers(connectionSocket, size, content_type, last_modified_date)
					else:
						send_error_headers(connectionSocket, "HTTP/1.1 404 FILE_NOT_FOUND")


			connectionSocket.close()
		except ConnectionResetError:
			pass

def handle_conditionals(items):
	for x in items:
		mod_text = "If-modified-since: "
		if re.search("^" + mod_text, x):
			return x[len(mod_text):]
	return None

def get_content_type(requested_item):
	if re.search(".(htm|html)$", requested_item):
		return "text/html"
	elif re.search(".(jpg|jpeg)$", requested_item):
		return "image"
	elif re.search(".txt$", requested_item):
		return "text/plain"

def send_error_headers(connectionSocket, error_line):
	
	headers = "Server: Scardox\r\n"
	tnow = datetime.now()
	tnowstr = tnow.strftime('%a, %d %b %Y %H:%M:%S') + " GMT"
	headers += "Date: " + tnowstr + " GMT" + crlf
	headers += crlf + crlf
	error_total = error_line + crlf + headers
	connectionSocket.send(error_total.encode())
	#connectionSocket.send(headers.encode())

def send_cond_headers(connectionSocket, size, content_type, last_modified):
	
	headers = "Server: Scardox\r\n"
	tnow = time.gmtime()
	tnowstr = time.strftime('%a, %d %b %Y %H:%M:%S', tnow)
	headers += "Date: " + tnowstr +" GMT"+ crlf
	headers += "Content-Length: " + str(size) + crlf
	headers += "Content-Type: " + content_type + crlf
	headers += "Last-Modified: " + last_modified.strftime('%a, %d %b %Y %H:%M:%S') + " GMT"
	headers += crlf + crlf
	connectionSocket.send("HTTP/1.0 304 NOT_MODIFIED\r\n".encode())
	connectionSocket.send(headers.encode())

def send_headers(connectionSocket, size, content_type, last_modified):
	
	headers = "Server: Scardox\r\n"
	tnow = datetime.utcnow()
	tnowstr = tnow.strftime('%a, %d %b %Y %H:%M:%S')
	headers += "Date: " + tnowstr + " GMT" + crlf
	headers += "Content-Length: " + str(size) + crlf
	headers += "Content-Type: " + content_type + crlf
	headers += "Last-Modified: " + last_modified.strftime('%a, %d %b %Y %H:%M:%S') + " GMT"
	headers += crlf + crlf
	connectionSocket.send("HTTP/1.0 200 OK\r\n".encode())
	connectionSocket.send(headers.encode())


def send_text(text, connectionSocket):
	mod_text = text + "\r\n"
	connectionSocket.send(mod_text.encode())


def find_header(headers, connectionSocket):
	for x in headers:
		finds = re.search("^Host: ", x)
		if finds:
			return True;
	send_error_headers(connectionSocket, "HTTP/1.1 400 MISSING_HOST")
	return False;

def check_request_line(request_line, connectionSocket):
	if len(request_line) > 3:
		send_error_headers(connectionSocket, "HTTP/1.1 400 TOO_MANY_ARGUMENTS")
		return False
	elif len(request_line) < 3:
		send_error_headers(connectionSocket, "HTTP/1.1 400 TOO_FEW_ARGUMENTS")
		return False		
	elif not request_line[0] == 'GET':
		send_error_headers(connectionSocket, "HTTP/1.1 405 ONLY_GET_PERMITTED\r\nAllow: GET")
		return False 
	elif not request_line[2] == 'HTTP/1.1':
		send_error_headers(connectionSocket, "HTTP/1.1 505 WRONG_HTML_VERSION")
		return False
	elif not check_extension(request_line[1]):
		send_error_headers(connectionSocket, "HTTP/1.1 404 FILE_NOT_FOUND")
		return False

	return True
def load_file(requested_item):
	try:
		file = open(requested_item, 'rb')
		file_data = file.read()
		file.close()
		return file_data
	except OSError as e:
		return None

def send_file(file_data, connectionSocket):
	try:
		connectionSocket.send(file_data)	
	except ConnectionResetError:
		send_error_headers(connectionSocket, "HTTP/1.1 500 SERVER_RESET")

def check_extension(requested_item):
	regexp = "(" + "|".join(allowed_extensions) + ")$"
	return bool(re.search(regexp, requested_item))

run();
