class RDTHeader():
    def __init__(self, SYN: int = 0, FIN: int = 0, ACK: int = 0, SEQ_num: int = 0, ACK_num: int = 0, LEN: int = 0,
                 CHECKSUM: int = 0, PAYLOAD=None, RWND: int = 0) -> None:
        self.test_case = 0  # Indicate the test case that will be used

        self.SYN = SYN  # 1 bytes
        self.FIN = FIN  # 1 bytes
        self.ACK = ACK  # 1 bytes
        self.SEQ_num = SEQ_num  # 4 bytes
        self.ACK_num = ACK_num  # 4 bytes
        self.LEN = LEN  # 4 bytes
        self.CHECKSUM = CHECKSUM  # 2 bytes
        self.PAYLOAD = PAYLOAD  # Data LEN bytes
        # self.CWND = CWND                      # Congestion window size 4 bytes
        self.RWND = RWND  # Notification window size 4 bytes
        self.Reserved = 0  # Reserved field for any attribte you need.

        self.Source_address = [127, 0, 0, 1, 12244]  # Souce ip and port
        self.Target_address = [127, 0, 0, 1, 12249]  # Target ip and port

    def to_bytes(self):
        test_case = self.test_case.to_bytes(1, 'big')
        Source_address = self.Source_address[0].to_bytes(1, 'big') + self.Source_address[1].to_bytes(1, 'big') + \
                         self.Source_address[2].to_bytes(1, 'big') + self.Source_address[3].to_bytes(1, 'big') + \
                         self.Source_address[4].to_bytes(2, 'big')

        Target_address = self.Target_address[0].to_bytes(1, 'big') + self.Target_address[1].to_bytes(1, 'big') + \
                         self.Target_address[2].to_bytes(1, 'big') + self.Target_address[3].to_bytes(1, 'big') + \
                         self.Target_address[4].to_bytes(2, 'big')

        SYN = self.SYN.to_bytes(1, 'big')
        FIN = self.FIN.to_bytes(1, 'big')
        ACK = self.ACK.to_bytes(1, 'big')
        SEQ_num = self.SEQ_num.to_bytes(4, 'big')
        ACK_num = self.ACK_num.to_bytes(4, 'big')
        LEN = self.LEN.to_bytes(4, 'big')
        RWND = self.RWND.to_bytes(4, 'big')
        CHECKSUM = self.CHECKSUM.to_bytes(2, 'big')
        PAYLOAD = self.PAYLOAD.encode() if isinstance(self.PAYLOAD, str) else "".encode()
        Reserved = self.Reserved.to_bytes(8, 'big')

        # Join all bytes data together
        data = b''.join([SYN, FIN, ACK, SEQ_num, ACK_num, LEN, RWND, CHECKSUM, Reserved, PAYLOAD])

        # Calculate checksum
        checksum = 0
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                checksum += int.from_bytes(data[i:i + 2], 'big')
            else:
                checksum += int.from_bytes(data[i:i + 1] + b'\x00', 'big')
        while checksum > 0xffff:
            checksum = (checksum & 0xffff) + (checksum >> 16)
        checksum = ~checksum & 0xffff

        # Replace checksum field
        CHECKSUM = checksum.to_bytes(2, 'big')

        return b''.join(
            [test_case, Source_address, Target_address, SYN, FIN, ACK, SEQ_num, ACK_num, LEN, RWND, CHECKSUM, Reserved,
             PAYLOAD])

    def from_bytes(self, data):
        if not data:
            return self
        self.test_case = data[0]
        Source_address = []
        for i in range(4):
            Source_address.append(data[i + 1])
        Source_address.append(int.from_bytes(data[5:7], 'big'))
        self.Source_address = Source_address

        Target_address = []
        for i in range(4):
            Target_address.append(data[i + 7])
        Target_address.append(int.from_bytes(data[11:13], 'big'))
        self.Target_address = Target_address

        self.SYN = data[13]
        self.FIN = data[14]
        self.ACK = data[15]
        self.SEQ_num = int.from_bytes(data[16:20], 'big')
        self.ACK_num = int.from_bytes(data[20:24], 'big')
        self.LEN = int.from_bytes(data[24:28], 'big')
        self.RWND = int.from_bytes(data[28:32], 'big')
        self.CHECKSUM = int.from_bytes(data[32:34], 'big')
        self.Reserved = int.from_bytes(data[34:42], 'big')

        self.PAYLOAD = data[42:].decode()

        # Verify checksum
        checksum = 0
        for i in range(13, len(data), 2):
            if i == 31:
                checksum += int.from_bytes(data[i:i + 1] + b'\x00', 'big')
            else:
                if i == 33:
                    checksum += int.from_bytes(b'\x00' + data[i + 1: i + 2], 'big')
                else:
                    if i + 1 < len(data):
                        checksum += int.from_bytes(data[i:i + 2], 'big')
                    else:
                        checksum += int.from_bytes(data[i:i + 1] + b'\x00', 'big')

        while checksum > 0xffff:
            checksum = (checksum & 0xffff) + (checksum >> 16)
        checksum = ~checksum & 0xffff

        if checksum != self.CHECKSUM:
            raise ValueError("Incorrect checksum!")

        return self


    def assign_address(self, Source_address: tuple, Target_address: tuple):
        source_ip = Source_address[0].split('.')
        target_ip = Target_address[0].split('.')
        for i in range(4):
            self.Source_address[i] = int(source_ip[i])
            self.Target_address[i] = int(target_ip[i])
        self.Source_address[4] = Source_address[1]
        self.Target_address[4] = Target_address[1]


    @property
    def src(self):
        return (f"{self.Source_address[0]}.{self.Source_address[1]}.{self.Source_address[2]}.{self.Source_address[3]}",
                self.Source_address[4])


    @property
    def tgt(self):
        return (f"{self.Target_address[0]}.{self.Target_address[1]}.{self.Target_address[2]}.{self.Target_address[3]}",
                self.Target_address[4])
