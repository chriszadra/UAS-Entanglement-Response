import time
import board
import busio
import digitalio
import Jon_rfm95
import struct
'''
def receive(timeout=5):
    print("Special Receiving...")
    packet = Radio.receive(timeout)
    if packet is None:
        print("No Packet Received")
    elif packet[0]==0:
        print("Drop the hook!")
    elif packet[0]==1:
        print("Drop the Droge")
    elif packet[0]==2:
        print("Updating perameters")
    elif packet[0]==3:
        print("Sending perameters")
    else:
        print("Unknown Packet Received")
    print(packet)
    return packet
'''
print("test")
RADIO_FREQ_MHZ=915.0
RadioDIO0 = digitalio.DigitalInOut(board.RFM_IO0)
RadioDIO0.direction = digitalio.Direction.INPUT
CS = digitalio.DigitalInOut(board.RFM_CS)
RESET = digitalio.DigitalInOut(board.RFM_RST)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
Radio = Jon_rfm95.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
Radio.spreading_factor = 9
Radio.signal_bandwidth = 125000  # Set signal bandwidth to 125 kHz
Radio.coding_rate = 6   # Set coding rate to 4/5
'''
def droneRadio():
    Radio.send(b"ff")#send an integer of the load on the loadcell to the GS
    packet = Radio.receive(timeout=0.1)
    if packet is None:
        print("No Packet Received")
    else:
        print("Received:", packet)
        if packet[0] == 0:
            dropHook()
        elif packet[0] == 1:
            dropDrouge()
        elif packet[0] == 2:
            print("Updating parameters")
        elif packet[0] == 3:
            print("Sending parameters")
        else:
            print("Unknown Packet Received")
'''
Radio.receive(keep_listening=True)  # Start listening for packets
print(dir(board))
while(True):
    print("Waiting for packet...")
    print(RadioDIO0.value)
    if RadioDIO0.value:
        print(Radio.getLastPacket())
        print(Radio.rx_done())
        time.sleep(1)
