import copy
import threading
import socket
import random
import time
from Header import RDTHeader

# fromSenderAddr = ('127.0.0.1', 12345)
# toReceiverAddr = ('127.0.0.1', 12346)
# fromReceiverAddr = ('127.0.0.1', 12347)
# toSenderAddr = ('127.0.0.1', 12348)

proxy_server_address = ('10.16.52.94', 12234)   # ProxyServerAddress
fromSenderAddr = ('10.16.52.94', 12345)         # FromSender
toReceiverAddr = ('10.16.52.94', 12346)         # ToSender
fromReceiverAddr = ('10.16.52.94', 12347)       # FromReceiver
toSenderAddr = ('10.16.52.94', 12348)           # ToReceiver

class RDTSocket():
    def __init__(self, TYPE) -> None:
        """
        You shold define necessary attributes in this function to initialize the RDTSocket
        """
        self.type = TYPE  # 'client' or 'server'
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.local_address = None
        self.connections = {}
        self.buffer = {}

    def bind(self, address: (str, int)):  # type: ignore
        """
        When trying to establish a connection. The socket must be bound to an address 
        and listening for connections. address is the address bound to the socket on 
        the other end of the connection.
        params: 
            address:    Target IP address and its port
        """
        self.socket.bind(address)
        self.local_address = address
        # raise NotImplementedError()

    def accept(self):  # type: ignore
        """
        When using this SOCKET to create an RDT SERVER, it should accept the connection
        from a CLIENT. After that, an RDT connection should be established.
        Please note that this function needs to support multithreading and be able to 
        establish multiple socket connections. Messages from different sockets should 
        be isolated from each other, requiring you to multiplex the data received at 
        the underlying UDP.

        This function should be blocking. 

        """
        seq_num = 0
        while True:
            data, addr = self.socket.recvfrom(1024)
            header = RDTHeader().from_bytes(data)
            if header.SYN == 1 and header.ACK == 0:
                print("[server: SYN received]")
                response = RDTHeader(SYN=1, ACK=1, SEQ_num=seq_num, ACK_num=header.SEQ_num + 1)
                response.assign_address(self.local_address, header.src)
                self.socket.sendto(response.to_bytes(), fromReceiverAddr)
            if header.SYN == 0 and header.ACK == 1 and header.ACK_num == seq_num + 1:
                print("[server: ACK received]")
                self.connections[header.src] = 1
                break

    def connect(self, address: (str, int)):  # type: ignore
        """
        When using this SOCKET to create an RDT client, it should send the connection
        request to target SERVER. After that, an RDT connection should be established.
        
        params:
            address:    Target IP address and its port
        """
        # send SYN packet
        while True:
            seq_num = 0
            header = RDTHeader(SYN=1, SEQ_num=seq_num)
            header.assign_address(self.local_address, address)
            self.socket.sendto(header.to_bytes(), fromSenderAddr)
            print("[client: SYN sent]")

            # receive SYN-ACK packet (if timeout, then resend SYN)
            self.socket.settimeout(5.0)
            try:
                data, addr = self.socket.recvfrom(1024)
            except socket.timeout:
                continue
            self.socket.settimeout(None)
            response = RDTHeader().from_bytes(data)
            if response.SYN == 1 and response.ACK == 1 and response.ACK_num == seq_num + 1:
                print("[client: SYN-ACK received]")
                acknowledge = RDTHeader(ACK=1, SEQ_num=response.ACK_num, ACK_num=response.SEQ_num + 1)
                acknowledge.assign_address(self.local_address, address)
                self.socket.sendto(acknowledge.to_bytes(), fromSenderAddr)
                self.connections[address] = 1
                break

    def send(self, data=None, tcpheader=None, test_case=0):
        """
        RDT can use this function to send specified data to a target that has already 
        established a reliable connection. Please note that the corresponding CHECKSUM 
        for the specified data should be calculated before computation. Additionally, 
        this function should implement flow control during the sending phase. Moreover, 
        when the data to be sent is too large, this function should be able to divide 
        the data into multiple chunks and send them to the destination in a pipelined 
        manner.
        
        params:
            data:       The data that will be sent.
            tcpheader:  Message header.Include SYN, ACK, FIN, CHECKSUM, etc. Use this
                        attribute when needed.
            test_case:  Indicate the test case will be used in this experiment
        """
        if tcpheader is None:
            tcpheader = {'SYN': 0, 'ACK': 0, 'FIN': 0}
        packet = RDTHeader(**tcpheader)
        packet.PAYLOAD = data
        for addr in self.connections:
            packet.assign_address(self.local_address, addr)
        packet.LEN = len(data.encode()) if data else 0
        self.socket.sendto(packet.to_bytes(), fromSenderAddr)
        print("socket sent")

    def recv(self):
        """
        You should implement the basic logic for receiving data in this function, and 
        verify the data. When corrupted or missing data packets are detected, a request 
        for retransmission should be sent to the other party.
        
        This function should be bolcking.
        """
        while True:
            data, addr = self.socket.recvfrom(1024)
            response = RDTHeader().from_bytes(data)
            if response.SYN == 0 and response.ACK == 0 and response.FIN == 0:  # expected should be adjusted based on protocol state
                # Process data or control messages
                if response.src not in self.buffer:
                    self.buffer[response.src] = []
                self.buffer[response.src].append(response.PAYLOAD)
            if response.SYN == 0 and response.ACK == 0 and response.FIN == 1:
                output = copy.deepcopy(self.buffer[response.src])
                self.close()
                return output

    def close(self):
        """
        Close current RDT connection.
        You should follow the 4-way-handshake, and then the RDT connection will be terminated.
        """
        tgt = None
        for addr in self.connections:
            tgt = addr
        if self.type == 'client':
            while True:
                fin = RDTHeader(FIN=1)
                fin.assign_address(self.local_address, tgt)
                self.socket.sendto(fin.to_bytes(), fromSenderAddr)
                print("[client: FIN sent]")
                self.socket.settimeout(5.0)
                try:
                    data, addr = self.socket.recvfrom(1024)
                except socket.timeout:
                    continue
                self.socket.settimeout(5.0)
                finack_packet = RDTHeader().from_bytes(data)
                if finack_packet.SYN == 0 and finack_packet.ACK == 1 and finack_packet.FIN == 0:
                    try:
                        data, addr = self.socket.recvfrom(1024)
                    except socket.timeout:
                        continue
                    self.socket.settimeout(None)
                    finack_packet = RDTHeader().from_bytes(data)
                    if finack_packet.SYN == 0 and finack_packet.ACK == 1 and finack_packet.FIN == 1:
                        ack = RDTHeader(ACK=1)
                        fin.assign_address(self.local_address, tgt)
                        self.socket.sendto(ack.to_bytes(), fromSenderAddr)
                        print("[client: ACK sent]")
                        time.sleep(1)
                        break
        else:
            ack = RDTHeader(ACK=1)
            ack.assign_address(self.local_address, tgt)
            self.socket.sendto(ack.to_bytes(), fromReceiverAddr)
            print("[server: ACK sent]")
            finack = RDTHeader(FIN=1, ACK=1)
            finack.assign_address(self.local_address, tgt)
            self.socket.sendto(finack.to_bytes(), fromReceiverAddr)
            print("[server: FIN-ACK sent]")
        self.socket.close()
        self.buffer.clear()
        self.connections.clear()
