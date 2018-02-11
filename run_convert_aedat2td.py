
# [header] [events] [header] [events] [header] [events] ... [header] [events]
#
# The header format is:
#
# uint16_t eventType
# uint16_t eventSource
# uint32_t eventSize
# uint32_t eventTSOffset
# uint32_t eventTSOverflow
# uint32_t eventCapacity
# uint32_t eventNumber
# uint32_t eventValid
#
# An events block contains eventNumber events.
#
# Each event is:
#
# uint32_t data
# uint32_t timestamp
#
# uint32_t data contains the x, y coordinates and polarity of the events.
# These values can be retrieved with the following binary operations:
#
# x = ( data >> 17 ) & 0x00001FFF
# y = ( data >> 2 ) & 0x00001FFF
# polarity = ( data >> 1 ) & 0x00000001

from struct import unpack, pack
import numpy as np
import libUnpackAtis as ua
import csv

aedatfile = "user01_fluorescent.aedat"
csvfile = "user01_fluorescent_labels.csv"

############# USEFULL FUNCTIONS ######################
def peek(f, length=1):
    pos = f.tell()
    data = f.read(length)
    f.seek(pos)
    return data

def readHeader(file):
    line = file.readline()
    if line != b'#!AER-DAT3.1\r\n':
        print('Wrong format: not AER-DAT3.1')
    while peek(file) == b'#':
        line = file.readline()
        # print(line)

def readEventCommonHeader(file):
    """ read common header of aedat 3.1 format """
    eventType = unpack('H',file.read(2))[0]
    eventSource = unpack('H',file.read(2))[0]
    eventSize = unpack('I', file.read(4))[0]
    eventTSOffset = unpack('I', file.read(4))[0]
    eventTSOverflow = unpack('I', file.read(4))[0]
    eventCapacity = unpack('I', file.read(4))[0]
    eventNumber = unpack('I', file.read(4))[0]
    eventValid = unpack('I', file.read(4))[0]
    if eventType != 1:
        print("Not Polarity Events!")
    return (eventType, eventSource, eventSize, eventTSOffset, eventTSOverflow, eventCapacity, eventNumber, eventValid)

def readPolarityEvent(file):
    """ read a polarity event in aedat 3.1 format """
    data = unpack('I', file.read(4))[0]
    timestamp = unpack('I', file.read(4))[0]
    validity = data & 0x00000001
    if validity:
        x = ( data >> 17 ) & 0x00001FFF
        y = ( data >> 2 ) & 0x00001FFF
        polarity = ( data >> 1 ) & 0x00000001
        return (timestamp, x, y , polarity)
    else:
        return None

def assessNumberOfPolarityEventsInFile(file):
    totalPolarityEventsInFile = 0
    while peek(file):
        commonHeader = readEventCommonHeader(file)
        eventNumber = commonHeader[6]
        if commonHeader[0] == 1: # if these are Polarity Events
            totalPolarityEventsInFile += commonHeader[7]
            for ii in np.arange(eventNumber):
                data = unpack('I', file.read(4))[0] # not stored yet
                timestamp = unpack('I', file.read(4))[0] # not stored yet
            if commonHeader[7] != eventNumber:
                print('unvalid events!')

    print('Number of polarity events: {0}'.format(totalPolarityEventsInFile))
    return totalPolarityEventsInFile

def readPolarityEventsInFile(totalPolarityEventsInFile, file):
    """ read events from a file and load them into numpy arrays """
    k = 0
    ts = np.zeros(totalPolarityEventsInFile, dtype = np.int64)
    coords = np.zeros((totalPolarityEventsInFile, 2), dtype = np.int16)
    pol = np.zeros(totalPolarityEventsInFile, dtype = np.bool)

    while peek(file):
        commonHeader = readEventCommonHeader(file)
        eventNumber = commonHeader[6]
        if commonHeader[0] == 1: # if these are Polarity Events
            for ii in np.arange(eventNumber):
                e = readPolarityEvent(file)
                if e != None:
                    ts[k], coords[k,0], coords[k,1], pol[k] = e
                    k += 1

            if commonHeader[7] != eventNumber:
                print('unvalid events!')
        else:
            print('Not Polarity Events! (not handled)')
    return ts, coords, pol

def readAllPolarityEventsFromAEDATFile(aedatfile):
    print('Reading aedat file... (' + aedatfile + ')')
    file = open(aedatfile,'rb')

    # read file header
    readHeader(file)

    # first assess the number of events in the file
    pos = file.tell()
    totalPolarityEventsInFile = assessNumberOfPolarityEventsInFile(file)
    file.seek(pos)

    # put events in lists
    ts, coords, pol = readPolarityEventsInFile(totalPolarityEventsInFile, file)

    file.close()

    return ts, coords, pol

def readLabelsFromCsvFile(csvfile):
    print('Reading CSV file... (' + csvfile + ')')
    labels_raw = []
    with open(csvfile, newline='') as currentcsvfile:
        values = csv.reader(currentcsvfile, delimiter=',', quotechar='|')
        for row in values:
            # print(', '.join(row))
            labels_raw.append(row)
    return np.array(labels_raw[1:]).astype(np.int64)

###############################################################

# read the aedat file
ts, coords, pol = readAllPolarityEventsFromAEDATFile(aedatfile)

# read the csv file
labels = readLabelsFromCsvFile(csvfile)

for idr, row in enumerate(labels):
    ind = (ts > row[1]) & (ts < row[2])

    td_savename = str(row[0]) + '_' + aedatfile[:-6] + '_' + str(idr) + '_td.dat'

    ua.writeATIS_td(td_savename, ts[ind], coords[ind,:], pol[ind])
