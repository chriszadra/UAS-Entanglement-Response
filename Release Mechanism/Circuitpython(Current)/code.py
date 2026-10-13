# =========================
# USER SETTINGS
# =========================

# Load cell
LoadLimitN = 40.0
loadTolerance = 200

COUNTS_PER_NEWTON = 165  # determined via calibration procedure 
corrections = [1.0, 1.0, 1.0]  # corrections for different loading ranges as needed, if not linear

ZERO_DEADBAND_N = 2.0

AVERAGE_WINDOW_S = 1.0
PRINT_INTERVAL_S = 1.0
BUFFER_WINDOW_S = 5.0

# Radio
radioTimeoutEnabled = False
timeoutPeriod = 5.0       # seconds
telemetryEnabled = True

# Servo
servoAngleOpen = 27
servoAngleClosed = 0


# =========================
# IMPORTS
# =========================

import time
import supervisor
import board
import pwmio
import busio
import digitalio
import Jon_rfm95
# import sdcardio
import adafruit_sdcard
import storage

from adafruit_motor import servo
from cedargrove_nau7802 import NAU7802

# Disable CircuitPython filesystem auto-reload so SD activity cannot be interrupted
supervisor.runtime.autoreload = False


# =========================
# GLOBAL VARIABLES
# =========================

hookServo = None
drougeServo = None

LoadCell = None
loadZero = 0.0
loadHistory = []

Radio = None
RadioDIO0 = None

lastRadioTime = 0
lastTelemTime = 0
lastPrintTime = 0
lastLoadTime = 0

counter = 0

SDCard = None
sdAvailable = False
spi = None

manualRelease = False
automaticRelease = False

loadLogBuffer = []
releaseDataWritten = False


# =========================
# SERVO FUNCTIONS
# =========================

def dropHook():
    print("Dropping hook")
    hookServo.angle = servoAngleOpen


def dropDrouge():
    print("Dropping drouge")
    drougeServo.angle = servoAngleOpen


def closeHook():
    print("Closing hook")
    hookServo.angle = servoAngleClosed


def closeDrouge():
    print("Closing drouge")
    drougeServo.angle = servoAngleClosed


def setupServos():
    global hookServo, drougeServo

    pwm1 = pwmio.PWMOut(
        board.D10,
        duty_cycle=2 ** 15,
        frequency=50
    )

    pwm2 = pwmio.PWMOut(
        board.D12,
        duty_cycle=2 ** 15,
        frequency=50
    )

    hookServo = servo.Servo(pwm1)
    drougeServo = servo.Servo(pwm2)

    hookServo.angle = servoAngleClosed
    drougeServo.angle = servoAngleClosed

    print("Servos ready")


# =========================
# LOAD CELL FUNCTIONS
# =========================

def setupLoadCell():
    global LoadCell

    i2c = busio.I2C(board.SCL, board.SDA)

    LoadCell = NAU7802(i2c)
    LoadCell.gain = 1

    print("NAU7802 created")


def tareLoadCell():
    """
    Collect 100 readings with no force applied, then determine
    the zero raw count from several readings.
    """

    global loadZero, loadHistory

    print("Remove all force from the load cell.")
    print("Taring in 5 seconds...")

    time.sleep(5)

    readings = []

    for _ in range(100):
        try:
            readings.append(LoadCell.read())
        except Exception as e:
            print("Tare read failed:", e)

        time.sleep(0.02)

    if len(readings) == 0:
        raise RuntimeError("Could not get any load cell readings during tare")

    loadZero = sum(readings) / len(readings)

    # Important: clear old force history after changing zero
    loadHistory = []

    print("Startup zero:", loadZero)


def rawToNewtons(raw):
    """
    Convert raw counts to force.

    Absolute value is intentional because the load cell
    sometimes changes sign depending on bending direction.
    """

    countDifference = raw - loadZero

    forceN = countDifference / COUNTS_PER_NEWTON

    return forceN


def newtonsToPounds(forceN):
    return forceN * 0.224809


def calibrateForce(indicatedN):

    if indicatedN < ZERO_DEADBAND_N:
        return indicatedN

    elif indicatedN <= 24.2:
        correctedN = indicatedN * corrections[0]

    elif indicatedN <= 41.2:
        correctedN = 22.24 + (indicatedN - 24.2) * corrections[1]

    else:
        correctedN = 44.48 + (indicatedN - 41.2) * corrections[2]

    return correctedN


def updateLoadAverage(raw):
    """
    Add the newest raw reading and retain only measurements
    from approximately the previous 1 second.

    Returns:
        averageN
        averageRaw
        deltaRaw
    """

    global loadHistory

    now = time.monotonic()

    # Store RAW counts so we can see the actual sensor behavior
    loadHistory.append((now, raw))

    # Remove samples older than our averaging window
    cutoffTime = now - AVERAGE_WINDOW_S

    while len(loadHistory) > 0 and loadHistory[0][0] < cutoffTime:
        loadHistory.pop(0)

    # Average the raw counts
    totalRaw = 0.0

    for sampleTime, sampleRaw in loadHistory:
        totalRaw += sampleRaw

    averageRaw = totalRaw / len(loadHistory)

    # Difference between averaged raw reading and startup zero
    deltaRaw = averageRaw - loadZero

    # Convert averaged delta to indicated force
    indicatedN = abs(deltaRaw) / COUNTS_PER_NEWTON

    # Apply existing calibration corrections
    averageN = calibrateForce(indicatedN)

    return averageN, averageRaw, deltaRaw


def readLoadCell():
    global lastLoadTime

    try:
        raw = LoadCell.read()

        lastLoadTime = time.monotonic()

        averageN, averageRaw, deltaRaw = updateLoadAverage(raw)

        return raw, averageN, averageRaw, deltaRaw

    except Exception as e:

        print("Reading load cell failed:", e)

        if time.monotonic() - lastLoadTime > 1.0:
            print("Load cell failed for more than 1 second")

            dropDrouge()
            dropHook()

        return None


def printLoad(raw, averageN, averageRaw, deltaRaw):
    global lastPrintTime

    now = time.monotonic()

    if now - lastPrintTime >= PRINT_INTERVAL_S:

        averageLb = newtonsToPounds(averageN)

        print(
            "Raw:", raw,
            "| AvgRaw:", round(averageRaw, 1),
            # "| Delta:", round(deltaRaw, 1),
            "| Average:", round(averageN, 2), "N",
            "|", round(averageLb, 2), "lb"
        )

        lastPrintTime = now


def checkLoadLimit(averageN):
    global counter
    global automaticRelease

    # Once the automatic release has happened, do not trigger it again
    if automaticRelease:
        return

    if averageN > LoadLimitN:
        counter += 1

    elif counter > 0:
        counter -= 1

    else:
        counter = 0

    if counter > loadTolerance:

        print(
            "Load exceeded limit:",
            round(averageN, 2),
            "N"
        )

        automaticRelease = True

        dropHook()
        dropDrouge()

        counter = 0


# =========================
# RADIO FUNCTIONS
# =========================

def setupRadio():
    global Radio
    global RadioDIO0
    global spi

    print("Setting up radio pins")

    RADIO_FREQ_MHZ = 912.34

    RadioDIO0 = digitalio.DigitalInOut(board.RFM_IO0)
    RadioDIO0.direction = digitalio.Direction.INPUT

    CS = digitalio.DigitalInOut(board.RFM_CS)
    RESET = digitalio.DigitalInOut(board.RFM_RST)

    Radio = Jon_rfm95.RFM9x(
        spi,
        CS,
        RESET,
        RADIO_FREQ_MHZ
    )

    Radio.spreading_factor = 9
    Radio.signal_bandwidth = 500000
    Radio.coding_rate = 6

    Radio.receive()

    print("Radio created")


def droneRadio():
    global LoadLimitN
    global loadTolerance
    global radioTimeoutEnabled
    global timeoutPeriod
    global telemetryEnabled
    global manualRelease

    packet = Radio.getLastPacket()

    if packet is None:
        print("Packet received was None")
        return

    print("Received:", packet[0])

    if packet[0] == 116:       # 't' keep alive
        pass

    elif packet[0] == 104:     # 'h'
        manualRelease = True
        dropHook()

    elif packet[0] == 100:     # 'd'
        manualRelease = True
        dropDrouge()

    elif packet[0] == 117:     # 'u'

        print("Updating parameters")

        setting = int(packet[2])

        if setting == 48:
            LoadLimitN = int(packet[4:])
            print("Load limit:", LoadLimitN, "N")

        elif setting == 49:
            loadTolerance = int(packet[4:])
            print("Load tolerance:", loadTolerance)

        elif setting == 51:
            tareLoadCell()

        elif setting == 52:
            radioTimeoutEnabled = packet[4:] == b'E'
            print("Timeout enabled:", radioTimeoutEnabled)

        elif setting == 53:
            timeoutPeriod = int(packet[4:])
            print("Timeout:", timeoutPeriod, "seconds")

        elif setting == 54:
            telemetryEnabled = packet[4:] == b"Enabled"
            print("Telemetry enabled:", telemetryEnabled)

    elif packet[0] == 115:     # 's'
        print("Sending parameters")

    else:
        print("Unknown packet type")


def checkRadio():
    global lastRadioTime

    try:
        if RadioDIO0.value:
            droneRadio()
            lastRadioTime = time.monotonic()

    except Exception as e:
        print("Radio error:", e)


def checkRadioTimeout():

    if (
        radioTimeoutEnabled
        and time.monotonic() - lastRadioTime > timeoutPeriod
    ):

        print("Radio timed out")

        dropDrouge()
        dropHook()

        time.sleep(1)


def sendTelemetry(averageN):
    global lastTelemTime

    if not telemetryEnabled:
        return

    now = time.monotonic()

    if now - lastTelemTime >= 0.5:

        Radio.send(
            str(int(round(averageN))),
            keep_listening=True
        )

        lastTelemTime = now


# =========================
# SD CARD FUNCTIONS
# =========================

def setupSD():
    global SDCard
    global sdAvailable
    global spi

    print("Setting up SD card")

    SDCard = None
    sdAvailable = False
    sd_cs = None

    try:
        print("SD initialization")

        sd_cs = digitalio.DigitalInOut(board.D9)

        # Give the SD card time to settle before initialization
        time.sleep(1.0)

        sd_card = adafruit_sdcard.SDCard(
            spi,
            sd_cs
        )

        # Give the initialized card time to settle before mounting
        time.sleep(1.0)

        vfs = storage.VfsFat(sd_card)
        storage.mount(vfs, "/sd")

        SDCard = sd_card
        sdAvailable = True

        print("SD card mounted")

    except Exception as e:
        print("SD setup failed:", e)

        if sd_cs is not None:
            try:
                sd_cs.deinit()
            except Exception:
                pass

        SDCard = None

        print("SD unavailable - continuing without data logging")


def bufferLoadData(raw, averageRaw, averageN):
    global loadLogBuffer
    global releaseDataWritten

    if releaseDataWritten:
        return

    now = time.monotonic()

    # Save load data to RAM at a maximum of 10 Hz
    if len(loadLogBuffer) > 0:
        if now - loadLogBuffer[-1][0] < 0.1:
            return

    loadLogBuffer.append(
        (
            now,
            raw,
            averageRaw,
            averageN,
            manualRelease,
            automaticRelease
        )
    )

    # Keep at most 250 records = approximately 25 seconds at 10 Hz
    while len(loadLogBuffer) > 250:
        loadLogBuffer.pop(0)


def writeBufferedLoadData():
    global loadLogBuffer
    global releaseDataWritten
    global sdAvailable

    # Only attempt the release-data write once
    if releaseDataWritten:
        return

    releaseDataWritten = True

    if not sdAvailable:
        print("SD unavailable - release data not written")
        loadLogBuffer = []
        return

    print("Writing release data to SD card")

    try:
        with open("/sd/load_data.csv", "a") as file:

            for (
                sampleTime,
                raw,
                averageRaw,
                averageN,
                sampleManualRelease,
                sampleAutomaticRelease
            ) in loadLogBuffer:

                file.write(
                    "{},{},{},{},{},{}\n".format(
                        sampleTime,
                        raw,
                        averageRaw,
                        averageN,
                        sampleManualRelease,
                        sampleAutomaticRelease
                    )
                )

        print("Release data written to SD card")

    except Exception as e:
        print("SD write failed:", e)

    # Free the RAM after the one-time write attempt
    loadLogBuffer = []


# =========================
# MAIN SETUP
# =========================

def setup():
    global lastRadioTime
    global lastTelemTime
    global lastPrintTime
    global lastLoadTime
    global spi

    setupServos()

    print("Starting SPI")

    spi = busio.SPI(
        board.SCK,
        MOSI=board.MOSI,
        MISO=board.MISO
    )

    radio_cs = digitalio.DigitalInOut(board.RFM_CS)
    radio_cs.direction = digitalio.Direction.OUTPUT
    radio_cs.value = True

    # One SD initialization attempt only
    setupSD()

    radio_cs.deinit()

    setupRadio()

    setupLoadCell()

    tareLoadCell()

    print("TEST READ AFTER TARE")
    testRaw = LoadCell.read()
    print("TEST READ WORKED:", testRaw)

    now = time.monotonic()

    lastRadioTime = now
    lastTelemTime = now
    lastPrintTime = now
    lastLoadTime = now

    print("Entering main loop")


# =========================
# MAIN LOOP
# =========================

def main():

    setup()

    while True:

        checkRadio()
        checkRadioTimeout()

        result = readLoadCell()

        if result is None:
            continue

        raw, averageN, averageRaw, deltaRaw = result

        # Check release threshold EVERY load-cell sample
        checkLoadLimit(averageN)

        # Keep recent high-resolution load data in RAM.
        # Nothing is written to the SD card during normal operation.
        bufferLoadData(
            raw,
            averageRaw,
            averageN
        )

        # Serial output is still limited to once per second
        printLoad(raw, averageN, averageRaw, deltaRaw)

        # The servos are released first. Only after a manual or automatic
        # release has happened do we write the buffered data to the SD card.
        if manualRelease or automaticRelease:
            writeBufferedLoadData()

        sendTelemetry(averageN)


# =========================
# RUN
# =========================

main()