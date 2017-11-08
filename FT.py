import socket
import argparse
import os
import sys
import threading
import random
import time
import hashlib

class FileHandler:
    def __init__(self, filename, chunk):
        self.filepath = filename
        self.filename = str(os.path.basename(filename))
        if not os.path.exists(self.filename):
            print("[+]Creating file", self.filename)
            self.writeb(b"")
        elif os.path.exists(self.filename):
            if not os.path.exists(self.filepath):
                print("[-]File already exist, changing name")
                self.filename = self.filename.split(".")
                self.filename[0] += str(random.randint(10000))
                self.filename = ".".join(self.filename)

        self.filestat = os.stat(filename)
        self.chunk = chunk
        self.file_size = self.filestat.st_size
        self.hasher = hashlib.new("sha256")
        self.hash = 0
        self.hash_thread = threading.Thread(target=self._hash)


    def readb(self, chunk, cursor=0, readall=0):
        if readall:
            with open(self.filepath, "rb") as f:
                return f.read(self.file_size)
        else:
            with open(self.filepath, "rb") as f:
                f.seek(cursor)
                return f.read(chunk)

    def writeb(self, data, append=0):
        if append:
            with open(self.filename, "ab") as f:
                f.write(data)
        else:
            with open(self.filename, "wb") as f:
                f.write(data)

    def _hash(self):
        print("\n[+]Hashing the file")
        myrcursor = 0
        while True:
            print("\r[+]", round((myrcursor*100/self.file_size), 1), "%".rjust(1), flush=True, end="")
            self.hasher.update(self.readb(self.chunk, cursor=myrcursor))
            myrcursor += self.chunk
            if  myrcursor > self.file_size:
                print("\r[+]", str(100), "%".rjust(1), flush=True, end="")
                break


    def start_hash(self):
        self.hash_thread.start()

    def set_hash(self):
        self.start_hash()
        self.hash_thread.join()
        self.hash = self.hasher.hexdigest()




    def get_stats(self):
        if self.hash_thread.isAlive:
            print("[+]Waiting to finish the file hash")
            return 0
        else:
            return self.hash


class TCP:
    def __init__(self):
        self.ip = "localhost"
        self.port = 9999
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.uConn = self.tcp_socket
        self.uAdrr = None

    def _bind(self):
        self.tcp_socket.bind((self.ip, self.port))
        print("[+]Binding on", (self.ip, self.port))

    def _listen(self):
        self.tcp_socket.listen(1)

    def _accept(self):
        self.uConn, self.uAdrr = self.tcp_socket.accept()
        print("[+]Established connection with", self.uAdrr)

    def _connect(self):
        self.tcp_socket.connect((self.ip, self.port))
        print("[+]Connected to", (self.ip, self.port))

    def _send(self, data):
        self.uConn.send(data)

    def _recv(self, chunk):
        return self.uConn.recv(chunk)

    def close(self):
        self.tcp_socket.close()



class Client(TCP):
    def __init__(self, ip="localhost", port=9999):
        super().__init__()
        self.ip = ip
        self.port = port
        self.init()
        self._connect()

    def init(self):
        print("[+]Welcome to the client")

    def send(self, data):
        self._send(data)

    def recv(self, chunk):
        return self._recv(chunk)

class Server(TCP):
    def __init__(self, ip="localhost", port=9999):
        super().__init__()
        self.ip = ip
        self.port = port
        self.init()
        self._bind()

    def init(self):
        print("[+]Welcome to the server")

    def listen(self):
        self._listen()

    def send(self, data):
        self._send(data)

    def recv(self, chunk):
        return self._recv(chunk)

    def accept(self):
        self._accept()

def launch_server(ip, port, _files, chunk):
    server = Server(ip, port)
    server.listen()
    server.accept()
    number_files = int(server.recv(32).decode("utf8"))
    files = []
    server.send(b"1")
    print("[+]"+str(number_files), "files to receive")

    for i in range(number_files):
        filesize = int(server.recv(chunk).decode("utf8"))
        server.send(b"1")
        filename = str(server.recv(chunk).decode("utf8"))
        print("[+]file",filename,"with", str(filesize/1000000),"Mb")
        file = FileHandler(filename=filename, chunk=chunk)
        file.file_size = filesize
        files.append(file)
        server.send(b"1")
    print("[+]Starting the receive mode")
    multiple_recv(server, files, chunk)
    server.close()

def multiple_recv(server, files, chunk):
    for i in files:
        print("\n[+]Receiving", i.filename)
        data_recvd = 0
        max_lenght = i.file_size
        while True:
            mystr = "\r[+]Writing data "+ str(round((data_recvd*100/max_lenght), 1))
            print(mystr + "%".rjust(1), flush=True, end="")
            data = server.recv(chunk)
            i.writeb(data, append=1)
            data_recvd += sys.getsizeof(data)
            server.send(b"1")
            if data_recvd > max_lenght:
                mystr = "\r[+]Writing data "+ str(100)
                print(mystr + "%".rjust(1), flush=True, end="")
                break
        i.set_hash()
        server.send(b"1")
        client_hash = server.recv(1024).decode("utf8")
        print("\n[+]File", i.filename, "has been received successfully\n[+]sha256 hash:", i.hash)
        print("[+]Hash match : ", client_hash == i.hash, "\n")
        server.send(b"1")

    print("[+]All files has been received")
    server.send(b"1")


def launch_client(ip, port, _files, chunk):
    client = Client(ip, port)
    files = []
    number_files = 0
    for x in _files:
        files.append(FileHandler(x, chunk))
        number_files += 1

    print("[+]number of files:", number_files)
    client.send(str(number_files).encode("utf8"))
    client.recv(1024)
    #print("[+]Sending file size info")
    for file in files:
        client.send(str(file.file_size).encode("utf8"))
        client.recv(1024)
        client.send(file.filename.encode("utf8"))
        client.recv(1024)

    multiple_send(client, files, chunk)
    client.close()


def multiple_send(client, files, chunk):
    for file in files:
        print("\n[+]Sending", file.filename)
        file.cursor = 0
        while True:
            percent = str(round((file.cursor*100/file.file_size), 1))
            print("\r[+]Sending data", percent,"%".rjust(1), flush=True, end="")
            client.send(file.readb(chunk, cursor=file.cursor))
            file.cursor+= chunk
            client.recv(2)
            if file.cursor > file.file_size:
                percent = "100"
                print("\r[+]Sending data", percent,"%".rjust(1), flush=True, end="")
                break

        file.set_hash()
        client.recv(2)
        client.send(file.hash.encode("utf8"))
        client.recv(2)
        print("\n[+]" + file.filename, "has been sent successfully\n[+]sha256 hash:", file.hash, "\n")


    print("[+]All file has been sended")
    client.recv(2)

def Main(ip, port, files, recv=0, send=0, chunk=4096):
    os.system("cls")
    try:
        if recv:
            launch_server(ip, port, files, chunk)
        elif send:
            launch_client(ip, port, files, chunk)
        else:
            print["[-]No mode set"]
            exit()
    except KeyboardInterrupt:
        print("\n[-]Quitting the program")
        exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="default : ip localhost, port 9999, parse speed 20971520(bytes), checksum true")
    parser.add_argument("IP", help="Destination IP", type=str)
    parser.add_argument("PORT", help="Destination Port", type=int)
    parser.add_argument("-f", "--file", help="Files to send", type=str,
                        action="append")
    parser.add_argument("-ps", "--parse_speed",
                        help="define the chunk of memory to send in bytes //default 2mb\\",
                        type=int, default=20971520)
    parser.add_argument("-nc", "--nochecksum", help="Deactivate the checksum step", action="store_const", default=False, const=True)
    parser.add_argument("-sm", "--servermode", help="Bring the server mode", action="store_const", const=launch_server, default=False)
    parser.add_argument("-cm", "--clientmode", help="Bring the client mode", action="store_const", const=launch_client, default=False)
    args = parser.parse_args()

    if args.servermode:
        print("[+]Launching server mode")
        Main(args.IP, args.PORT, args.file, recv=1, chunk=args.parse_speed)
    elif args.clientmode != False:
        print("[+]Launching client mode")
        Main(args.IP, args.PORT, args.file, send=1, chunk = args.parse_speed)
    else:
        print("[+]No mode choosen.")
        exit()
