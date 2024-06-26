import socket
import time
from RDT import RDTSocket
from multiprocessing import Process
from ip import proxy_server_address, fromReceiverAddr, resultAddr, \
    sender_address, receiver_address, sender_address1

num_test_case = 16


class TimeoutException(Exception):
    pass


def handler(signum, frame):
    raise TimeoutException


# signal.signal(signal.SIGALRM, handler)
def test_case():
    sender_sock = None
    sender_sock1 = None
    reciever_sock = None

    # TODO: You could change the range of this loop to test specific case(s) in local test.

    for i in range(num_test_case):
        if sender_sock:
            del sender_sock
        if reciever_sock:
            del reciever_sock
        if sender_sock1:
            del sender_sock1
        sender_sock = RDTSocket(TYPE='client', testcase=i)  # You can change the initialize RDTSocket()
        reciever_sock = RDTSocket(TYPE='server', testcase=i)  # You can change the initialize RDTSocket()

        # if you want to use 2 senders and 1 receiver, please uncomment this line
        # sender_sock1 = RDTSocket(TYPE='client', testcase=i)  # You can change the initialize RDTSocket()
        print(f"Start test case : {i}")

        result = None
        try:
            result = RDT_start_test(sender_sock, sender_sock1, reciever_sock, sender_address, receiver_address, i)
        except Exception as e:
            print(e)
        finally:

            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect(resultAddr)

            client_sock.sendall(f"{sender_address}-{receiver_address}:{i}".encode())

            response = client_sock.recv(1024)

            client_sock.close()

            print(f"proxy result for test case {i} {response.decode()}")

            if response.decode() == 'True' and result:
                print(f"test case {i} pass")
            else:
                print(f"test case {i} fail: result = {result}")

            #############################################################################
            # TODO you should close your socket, and release the resource, this code just a
            # demo. you should make some changes based on your code implementation or you can
            # close them in the other places.

            #############################################################################
            time.sleep(5)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(f"{sender_address}-{receiver_address}".encode(), proxy_server_address)

            time.sleep(10)


def RDT_start_test(sender_sock, sender_sock1, reciever_sock, sender_address, receiver_address, test_case):
    sender = Process(target=RDT_send, args=(sender_sock, sender_address, receiver_address, test_case, 1))
    if sender_sock1 is not None:
        sender1 = Process(target=RDT_send, args=(sender_sock1, sender_address1, receiver_address, test_case, 2))
        receiver = Process(target=RDT_receive, args=(reciever_sock, receiver_address, test_case, 2))
    else:
        sender1 = None
        receiver = Process(target=RDT_receive, args=(reciever_sock, receiver_address, test_case, 1))

    receiver.start()
    time.sleep(5)
    sender.start()
    if sender_sock1 is not None:
        sender1.start()

    # if test_case < 5:
    #     signal.alarm(20)
    # else:
    #     signal.alarm(120)

    sender.join()
    if sender_sock1 is not None:
        sender1.join()
    receiver.join()
    time.sleep(1)

    # signal.alarm(0)

    if test_case < 5:
        return True
    else:
        a = test_file_integrity('original.txt', 'transmit_0.txt')
        b = test_file_integrity('original.txt', 'transmit_1.txt') if (sender_sock1 is not None) else True
        # TODO you may need to change the path, if you want.
        return a & b


def RDT_send(sender_sock: RDTSocket, source_address, target_address, test_case, sender_num=1):
    """
        You should refer to your own implementation to implement this code. the sender should specify the Source_address, Target_address, and test_case in the Header of all packets sent by the receiver.
        params:
            target_address:    Target IP address and its port
            source_address:    Source IP address and its port
            test_case:         The rank of test case
    """
    data_blocks = []
    file_path = 'original.txt'  # You can modify the path of file. Howerver, if you change this file, you need to modify the input for function test_file_integrity()

    sock = sender_sock

    sock.bind(source_address)
    sock.connect(target_address)
    print("Client connect successfully!")

    time.sleep(1.0)

    if test_case >= 5:
        #############################################################################
        # TODO: you need to send a files. Here you need to write the code according to your own implementation.

        with open('original.txt', 'r') as f:
            data = f.read()
            sock.send(data=data, test_case=test_case)
        time.sleep(sender_num)
        sock.close()
        #############################################################################

    else:

        #############################################################################
        # TODO: you need to send a short message. May be you can use:
        data = "Here is some text."
        sock.send(data=data, test_case=test_case)
        # data = "Here is another text."
        # sock.send(data=data, test_case=test_case)
        time.sleep(1.0)
        sock.close()

        # raise NotImplementedError
        #############################################################################


def RDT_receive(reciever_sock: RDTSocket, source_address, test_case, connect_num=1):
    """
        You should refer to your own implementation to implement this code. the receiver should specify the Source_address, Target_address, and test_case in the Header of all packets sent by the receiver.
        params: 
            source_address:    Source IP address and its port
            test_case:         The rank of test case
    """
    sock = reciever_sock
    sock.proxy_server_addr = fromReceiverAddr
    sock.bind(source_address)
    sock.accept(connect_num=connect_num)
    print("Server connect successfully!")

    connections = sock.recv()

    if test_case >= 5:
        #############################################################################
        # TODO: you need to receive original.txt from sender. Here you need to write the code according to your own implementation.

        # you should Save all data to the file (transmit.txt), and stop this loop when the client close the connection.
        # After that, you need to use the following function to verify the file that you received. When test_case >= 5, the test is passed only when test_file_integrity is verified and the proxy is verified.
        for i, addr in enumerate(connections):
            with open(f"transmit_{i}.txt", 'w') as f:
                f.write(connections[addr])
                print(f"received file from {addr[0]}:{addr[1]} and stored to 'transmit_{i}.txt'.")

    #############################################################################

    else:

        #############################################################################
        # TODO: you need to receive a short message. May be you can use:
        for addr in connections:
            print(f"received message from {addr[0]}:{addr[1]}:", connections[addr])

        # raise NotImplementedError
        #############################################################################


def test_file_integrity(original_path, transmit_path):
    with open(original_path, 'rb') as file1, open(transmit_path, 'rb') as file2:
        while True:
            block1 = file1.read(4096)
            block2 = file2.read(4096)

            if block1 != block2:
                return False

            if not block1:
                break

    return True


if __name__ == '__main__':
    test_case()
