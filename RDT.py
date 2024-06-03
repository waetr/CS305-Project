import random
import socket
import time
from Header import RDTHeader

# local server

# fromSenderAddr = ('127.0.0.1', 12345)
# toReceiverAddr = ('127.0.0.1', 12346)
# fromReceiverAddr = ('127.0.0.1', 12347)
# toSenderAddr = ('127.0.0.1', 12348)

# proxy server

fromSenderAddr = ('10.16.52.94', 12345)  # FromSender
toReceiverAddr = ('10.16.52.94', 12346)  # ToSender
fromReceiverAddr = ('10.16.52.94', 12347)  # FromReceiver
toSenderAddr = ('10.16.52.94', 12348)  # ToReceiver


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
        self.buffer = {}
        self.isn = 110 if TYPE == 'client' else 120

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
        while True:
            data, addr = self.socket.recvfrom(1024)
            try:
                header = RDTHeader().from_bytes(data)
            except ValueError:
                print("Incorrect checksum")
                continue
            if header.SYN == 1 and header.ACK == 0:
                response = RDTHeader(test_case=20, SYN=1, ACK=1, SEQ_num=self.isn, ACK_num=header.SEQ_num + 1)
                response.assign_address(self.local_address, header.src)
                print_header(response)
                self.socket.sendto(response.to_bytes(), fromReceiverAddr)
            if (header.SYN == 0 and header.ACK == 1 and header.ACK_num == self.isn + 1) or \
                    (header.SYN == 0 and header.ACK == 0 and header.LEN > 0):
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
            header = RDTHeader(test_case=20, SYN=1, SEQ_num=self.isn)
            header.assign_address(self.local_address, address)
            print_header(header)
            self.socket.sendto(header.to_bytes(), fromSenderAddr)

            # receive SYN-ACK packet (if timeout, resend SYN)
            self.socket.settimeout(3.0)
            try:
                data, addr = self.socket.recvfrom(1024)
                response = RDTHeader().from_bytes(data)
            except socket.timeout or ValueError:
                continue
            self.socket.settimeout(None)
            if response.SYN == 1 and response.ACK == 1 and response.ACK_num == self.isn + 1:
                acknowledge = RDTHeader(test_case=20, ACK=1, SEQ_num=response.ACK_num, ACK_num=response.SEQ_num + 1)
                acknowledge.assign_address(self.local_address, address)
                print_header(acknowledge)
                self.socket.sendto(acknowledge.to_bytes(), fromSenderAddr)
                self.connections[address] = 1
                self.isn += 1
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
                packet.SEQ_num = i
                for addr in self.connections:
                    packet.assign_address(self.local_address, addr)
                # transmit the packet
                self.socket.sendto(packet.to_bytes(), fromSenderAddr)
                time.sleep(0.05)

            time.sleep(0.2)
            # receive ACK packets
            self.socket.setblocking(False)
            while True:
                try:
                    data, addr = self.socket.recvfrom(1024)
                    ack = RDTHeader().from_bytes(data)
                    if ack.ACK == 1:
                        acked[ack.ACK_num] = True
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
            if self.testcase not in [8, 9]:
                if window_size > 0 and loss >= window_size / 2:
                    window_size = window_size // 2
                else:
                    if window_size < 8:
                        window_size = 1 if (window_size == 0) else window_size * 2


        self.socket.setblocking(True)
        print("")

    def recv(self):
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
            if response.SYN == 0 and response.ACK == 0 and response.FIN == 0:  # expected should be adjusted based on protocol state
                # Process data or control messages
                max_chunk = max(max_chunk, response.SEQ_num)
                if response.SEQ_num not in self.buffer:
                    self.buffer[response.SEQ_num] = response.PAYLOAD
                # send ACK message
                acknowledge = RDTHeader(test_case=self.testcase, ACK=1, ACK_num=response.SEQ_num)
                acknowledge.assign_address(self.local_address, response.src)
                self.socket.sendto(acknowledge.to_bytes(), fromReceiverAddr)
                # print_header(acknowledge)
            if response.SYN == 0 and response.ACK == 0 and response.FIN == 1:
                output = ""
                for i in range(max_chunk + 1):
                    output = output + self.buffer[i]
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
            finack_packet = None
            while True:
                fin = RDTHeader(test_case=20, FIN=1)
                fin.assign_address(self.local_address, tgt)
                self.socket.sendto(fin.to_bytes(), fromSenderAddr)
                print_header(fin)
                self.socket.settimeout(5.0)
                try:
                    data, addr = self.socket.recvfrom(1024)
                except socket.timeout:
                    continue
                self.socket.settimeout(None)
                finack_packet = RDTHeader().from_bytes(data)
                break
            while True:
                if finack_packet.SYN == 0 and finack_packet.ACK == 1 and finack_packet.FIN == 1:
                    ack = RDTHeader(test_case=20, ACK=1)
                    ack.assign_address(self.local_address, tgt)
                    self.socket.sendto(ack.to_bytes(), fromSenderAddr)
                    print_header(ack)
                    time.sleep(1)
                    break
                data, addr = self.socket.recvfrom(1024)
                finack_packet = RDTHeader().from_bytes(data)
        else:
            ack = RDTHeader(test_case=20, ACK=1)
            ack.assign_address(self.local_address, tgt)
            self.socket.sendto(ack.to_bytes(), fromReceiverAddr)
            print_header(ack)

            finack = RDTHeader(test_case=20, FIN=1, ACK=1)
            finack.assign_address(self.local_address, tgt)
            self.socket.sendto(finack.to_bytes(), fromReceiverAddr)
            print_header(finack)

            # resend finack 2 times if not acknowledged
            # self.socket.settimeout(10.0)
            # try:
            #     self.socket.recvfrom(1024)
            # except socket.timeout:
            #     self.socket.sendto(finack.to_bytes(), fromReceiverAddr)
            #     print_header(finack)

        self.socket.close()
        self.buffer.clear()
        self.connections.clear()
