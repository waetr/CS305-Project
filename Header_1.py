from Header import RDTHeader

if __name__ == '__main__':
    head = RDTHeader(SYN=0, ACK=0, LEN=7, PAYLOAD="fuckyou")
    data = head.to_bytes()
    response = RDTHeader().from_bytes(data)
    print(response.src, response.tgt)
