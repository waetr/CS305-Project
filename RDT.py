import random
import socket
import time
from Header import RDTHeader
from ip import fromSenderAddr, fromReceiverAddr

def print_header(header):
    print(
        f"[{header.src}->{header.tgt}]: SYN={header.SYN} FIN={header.FIN} ACK={header.ACK} SEQ_NUM={header.SEQ_num} ACK_NUM={header.ACK_num}")


class RDTSocket():
    def __init__(self, TYPE, testcase) -> None:
        """
        You shold define necessary attributes in this function to initialize the RDTSocket
        """
        self.testcase = testcase
        self.type = TYPE  # 'client' or 'server'
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.local_address = None
        self.connections = {}
        self.connected = 0
        self.buffer = [{} for _ in range(8)]  # maximum of 8 connections
        self.isn = 0  # control multiple send requests

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

    def accept(self, connect_num=1):  # type: ignore
        """
        When using this SOCKET to create an RDT SERVER, it should accept the connection
        from a CLIENT. After that, an RDT connection should be established.
        Please note that this function needs to support multithreading and be able to 
        establish multiple socket connections. Messages from different sockets should 
        be isolated from each other, requiring you to multiplex the data received at 
        the underlying UDP.

        This function should be blocking. 

        """
        while True:
            data, addr = self.socket.recvfrom(1024)
            header = RDTHeader().from_bytes(data)
            if header.SYN == 1 and header.ACK == 0:
                response = RDTHeader(src=self.local_address, tgt=header.src, test_case=20, SYN=1, ACK=1)
                print_header(response)
                self.socket.sendto(response.to_bytes(), fromReceiverAddr)
            if header.SYN == 0 and header.ACK == 1:
                self.connected += 1
                self.connections[header.src] = self.connected
                if self.connected == connect_num:
                    break

    def connect(self, address: (str, int)):  # type: ignore
        """
        When using this SOCKET to create an RDT client, it should send the connection
        request to target SERVER. After that, an RDT connection should be established.
        
        params:
            address:    Target IP address and its port
        """
        # send SYN packet
        header = RDTHeader(src=self.local_address, tgt=address, test_case=20, SYN=1)
        print_header(header)
        self.socket.sendto(header.to_bytes(), fromSenderAddr)

        # receive SYN-ACK packet
        data, addr = self.socket.recvfrom(1024)
        response = RDTHeader().from_bytes(data)
        if response.SYN == 1 and response.ACK == 1:
            acknowledge = RDTHeader(src=self.local_address, tgt=address, test_case=20, ACK=1)
            print_header(acknowledge)
            self.socket.sendto(acknowledge.to_bytes(), fromSenderAddr)
            self.connections[address] = len(self.connections)

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
            tcpheader = {'test_case': test_case, 'SYN': 0, 'ACK': 0, 'FIN': 0}
        # preprocess the packet
        chunks = [data[i:i + 256] for i in range(0, len(data), 256)]
        acked = {i: False for i in range(len(chunks))}
        # l_window: the leftmost side of the notification window
        l_window = 0
        window_size = 8

        while l_window < len(chunks):
            # send unsent chunks & resend unacknowledged chunks
            for i in range(l_window, min(len(chunks), l_window + window_size)):
                if acked[i]:
                    continue
                # define the packet
                packet = RDTHeader(**tcpheader)
                packet.PAYLOAD = chunks[i]
                packet.LEN = len(chunks[i].encode())
                packet.SEQ_num = i + self.isn
                for addr in self.connections:
                    packet.assign_address(self.local_address, addr)
                # transmit the packet
                self.socket.sendto(packet.to_bytes(), fromSenderAddr)
                time.sleep(0.07)

            time.sleep(0.3)
            # receive ACK packets
            self.socket.setblocking(False)
            while True:
                try:
                    data, addr = self.socket.recvfrom(1024)
                    ack = RDTHeader().from_bytes(data)
                    if ack.ACK == 1:
                        acked[ack.ACK_num - self.isn] = True
                except BlockingIOError:
                    break
                except ValueError:
                    continue

            # compute packet loss rate
            loss = 0
            for i in range(l_window, min(len(chunks), l_window + window_size)):
                if not acked[i]:
                    loss += 1

            # move the notification window
            print(f'\rloss rate: {loss}/{window_size}, sent {l_window}/{len(chunks)}', end='')
            while l_window < len(chunks) and acked[l_window]:
                l_window += 1
                print(f'\rloss rate: {loss}/{window_size}, sent {l_window}/{len(chunks)}', end='')

            # congestion control: dynamically adjust window_size
            if self.testcase in [7, 12, 13, 14, 15]:
                if window_size > 0 and loss > window_size / 2:
                    window_size = window_size // 2
                else:
                    if window_size < 8:
                        window_size = 1 if (window_size == 0) else window_size * 2

        self.socket.setblocking(True)
        self.isn += len(chunks)
        print("")

    def recv(self):  # return value: data, addr
        """
        You should implement the basic logic for receiving data in this function, and 
        verify the data. When corrupted or missing data packets are detected, a request 
        for retransmission should be sent to the other party.
        
        This function should be bolcking.
        """
        max_chunk = 0
        while True:
            data, addr = self.socket.recvfrom(1024)
            try:
                response = RDTHeader().from_bytes(data)
            except ValueError:
                continue
            # record the index of this connection
            connection_idx = self.connections[response.src]
            if response.SYN == 0 and response.ACK == 0 and response.FIN == 0:  # expected should be adjusted based on protocol state
                # Process data or control messages
                max_chunk = max(max_chunk, response.SEQ_num)
                if response.SEQ_num not in self.buffer[connection_idx]:
                    self.buffer[connection_idx][response.SEQ_num] = response.PAYLOAD
                # send ACK message
                acknowledge = RDTHeader(test_case=self.testcase, ACK=1, ACK_num=response.SEQ_num)
                acknowledge.assign_address(self.local_address, response.src)
                self.socket.sendto(acknowledge.to_bytes(), fromReceiverAddr)
                # print_header(acknowledge)
            if response.SYN == 0 and response.ACK == 0 and response.FIN == 1:
                self.close(tgt=response.src)
                if self.connected == 0:
                    break
        for addr in self.connections:
            connection_idx = self.connections[addr]
            output = ""
            for i in range(max_chunk + 1):
                output = output + self.buffer[connection_idx][i]
            self.connections[addr] = output
        self.socket.close()
        return self.connections


    def close(self, tgt=None):
        """
        Close current RDT connection.
        You should follow the 4-way-handshake, and then the RDT connection will be terminated.
        """
        if tgt is None:
            for addr in self.connections:
                tgt = addr
        if self.type == 'client':
            # send FIN
            fin = RDTHeader(src=self.local_address, tgt=tgt, test_case=20, FIN=1)
            self.socket.sendto(fin.to_bytes(), fromSenderAddr)
            print_header(fin)
            # receive FIN-ACK and then send ACK
            while True:
                data, addr = self.socket.recvfrom(1024)
                finack_packet = RDTHeader().from_bytes(data)
                if finack_packet.SYN == 0 and finack_packet.ACK == 1 and finack_packet.FIN == 1:
                    ack = RDTHeader(src=self.local_address, tgt=tgt, test_case=20, ACK=1)
                    self.socket.sendto(ack.to_bytes(), fromSenderAddr)
                    print_header(ack)
                    break
        else:
            # send ACK
            ack = RDTHeader(src=self.local_address, tgt=tgt, test_case=20, ACK=1)
            self.socket.sendto(ack.to_bytes(), fromReceiverAddr)
            print_header(ack)
            # send FIN-ACK
            finack = RDTHeader(src=self.local_address, tgt=tgt, test_case=20, FIN=1, ACK=1)
            self.socket.sendto(finack.to_bytes(), fromReceiverAddr)
            print_header(finack)
        self.connected -= 1
