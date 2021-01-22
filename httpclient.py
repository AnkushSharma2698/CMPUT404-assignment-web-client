#!/usr/bin/env python3
# coding: utf-8
# Copyright 2016 Abram Hindle, https://github.com/tywtyw2002, and https://github.com/treedust
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it
debug = False

import sys
import socket
import re
# you may use urllib to encode data appropriately
from urllib.parse import urlparse, urlencode

# Define an exception
def help():
    print("httpclient.py [GET/POST] [URL]\n")

class HTTPResponse(object):
    def __init__(self, code=200, body=""):
        self.code = code
        self.body = body

class Request:
    def __init__(self, method, url, args = None):
        self.method = method
        self.host = url.hostname

        if url.path != "":
            self.path = url.path
        else:
            self.path = '/'

        if url.port:
            self.port = url.port
        else:
            self.port = 80
        # Holds all headers to be sent along in a request
        self.headers = {}
        # Holds the body of the request and must be parsed
        if args is None:
            self.body = ""
        else:
            self.body = urlencode(args) # Currently formats the data for url-form-encoded


    def form_request(self, protocol):
        # Forms the request to be sent

        # Setting the accept header to allow all incoming content types (Not sure if I should just limit it though?)
        request = "{method} {path} {protocol}\r\nHost:{host}\r\n".format(
            method     = self.get_method(),
            path       = self.get_path(),
            host       = self.get_host(),
            protocol   = protocol
        )
        # Parse and concat any additional headers set on the request
        for header_k, header_v in self.get_headers().items():
            request += "{key}:{value}\r\n".format(key=header_k, value=header_v)
        request+= "\r\n"

        # Handle Body if POST Request
        if self.get_method() == "POST":
            request += self.get_body()

        return request

    def set_header(self, k, v):
        self.headers[k] = v

    def get_headers(self):
        return self.headers

    def get_host(self):
        return self.host

    def get_port(self):
        return self.port

    def get_method(self):
        return self.method

    def get_path(self):
        return self.path

    def get_body(self):
        return self.body

class HTTPClient(object):
    protocol = "HTTP/1.1"
    user_agent = "404-HTTP-Client"
    #def get_host_port(self,url):

    # Will use this method to handle 404s
    def handle_exceptions(self, data):
        pass

    def connect(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        return None

    def get_code(self, data):
        # Split the data on spaces and the 1st index "should" contain the code
        data = data.split(' ')
        code = None
        try:
            code = int(data[1])
        except Exception as e:
            # Some unexpected error
            code = 500
        finally:
            return code

    def get_headers(self,data):
        return None

    def get_body(self, data):
        # The body of a response is evident after the headers are complete
        # Header completion is signified by a double carriage return and newline
        # re.DOTALL = True
        try:
            body = re.search("\r\n\r\n(.*)", data, flags=re.DOTALL)
            body = body.group(1)
        except Exception as e:
            # Some unexpected error
            body = ""
        finally:
            return body
    
    def sendall(self, data):
        self.socket.sendall(data.encode('utf-8'))

    def close(self):
        self.socket.close()

    # read everything from the socket
    def recvall(self, sock):
        buffer = bytearray()
        done = False
        while not done:
            part = sock.recv(1024)
            if (part):
                buffer.extend(part)
            else:
                done = not part
        return buffer.decode('utf-8')

    def GET(self, url, args=None):
        # Parse incoming url
        url = urlparse(url)

        if debug:
            print("GET : {url}".format(url=url))
        request = Request('GET', url)

        # Set any headers the GET request will need
        request.set_header("User-Agent", HTTPClient.user_agent)
        request.set_header("Accept", '*/*') # Accept any incoming content type
        request.set_header("Connection", "close") # Close the connection after one go, must specify since keep-alive is default on HTTP 1.1

        # Connect to the specified web resource
        if debug:
            print("Connecting to: {host}:{port}".format(host=request.get_host(), port=request.get_port()))
        self.connect(request.get_host(), request.get_port())

        # Send request to the resource
        request_str = request.form_request(HTTPClient.protocol)
        if debug:
            print("Sending: ", request_str.encode())
        self.sendall(request_str)

        # Receive result from resource
        data = self.recvall(self.socket)
        self.close()

        if debug:
            print("Response:", data)

        # Get the code returned
        code = self.get_code(data)
        body = self.get_body(data)

        return HTTPResponse(code, body)

    def POST(self, url, args=None):
        url = urlparse(url)
        if debug:
            print("POST : {url}".format(url=url))
        request = Request('POST', url, args)

        # Set headers for the POST request
        request.set_header("User-Agent", HTTPClient.user_agent)
        request.set_header("Accept", '*/*')  # Accept any incoming content type
        request.set_header("Connection", "close")  # Close the connection after one go, must specify since keep-alive is default on HTTP 1.1
        request.set_header("Content-Type", "application/x-www-form-urlencoded") # Currently the only content-type being handled
        request.set_header("Content-Length", len(request.get_body().encode('utf-8'))) # Content length may be 0, so this must be specified

        # Connect to the specified web resource
        if debug:
            print("Connecting to: {host}:{port}".format(host=request.get_host(), port=request.get_port()))
        self.connect(request.get_host(), request.get_port())

        # Send POST request to the resource
        request_str = request.form_request(HTTPClient.protocol)
        if debug:
            print("Sending:", request_str.encode())
        self.sendall(request_str)

        # Get response from the server
        data = self.recvall(self.socket)
        if debug:
            print("Response:", data)
        self.close()
        # Get code and body
        code = self.get_code(data)
        body = self.get_body(data)
        return HTTPResponse(code, body)

    def command(self, url, command="GET", args=None):
        if (command == "POST"):
            return self.POST( url, args )
        else:
            return self.GET( url, args )
    
if __name__ == "__main__":
    client = HTTPClient()
    command = "GET"
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) == 3):
        print(client.command( sys.argv[2], sys.argv[1] ))
    else:
        print(client.command( sys.argv[1] ))
