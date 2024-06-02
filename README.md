# CS305-2024Spring-FinalProject: Reliable Data Transfer upon UDP

The original code is available at: https://github.com/SUSTech-HPCLab/CS305-2024Spring-FinalProject.

## How to run

**Local test.** To test the project locally, run `proxy.py` first (and keep it running at the background); then run `test_case.py`. A successful test case will print the following message in the end:

``test case 0 pass``

**Online test.** To test the project based on the proxy server, first uncomment Lines 9-19 of `test_case.py`, comment Lines 25-33 of the same file, and perform similar steps at the beginning of `RDT.py`. Then modify Lines 18-19 of `test_case.py` to make sure the ip addresses is equal to your own machine. After that run `test_case.py`. The result is expected to be the same as in local test.

## What is done

The code can now pass Testcase 1.

Implemented features: 
1. three-way handshake and four-Way wavehand
2. Basic sender and receiver
3. Sender can send data multiple times to receiver, and receiver can store the data

Features under development:
1. Multithread in accept()
2. retransmitting
3. checksum verification (I have implemented the code in Header.py, where I only raise an error but does not handle it in the following codes)
4. big file transmission (chunking)
5. pipeline manner (congestion control, flow control, etc.)