#1/usr/bin/python
import socket
import sys
import os
import time
import threading
from torrentData import torrentData
from torrentPacket import torrentPacket

if (len(sys.argv) != 4):
	print('Usage: ')
	print('python3 sender.py')
	print('    <IP>')
	print('    <PORT>')
	print('    <MIN_TIME>')
	exit()

IP = sys.argv[1]
PORT = int(sys.argv[2])
MIN_TIME = int(sys.argv[3])

myID = -1
myState = torrentData()

SIG_DATA = False
SIG_TIME = False

#build torrentData from /Shared
for f in os.listdir("Shared"):
	myState.addFile(f, os.stat("Shared/" + f).st_size)

sf = len(myState.fileDict.keys())

#connect to tracker and recieve ID
def update_tracker():
	global myID
	global myState
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as h:
		h.connect((IP, PORT))
		h.sendall(torrentPacket.create_info(myID, myState).get_tcp_data())
		dataPak = h.recv(65536)
		data = torrentPacket.parse_tcp_data(dataPak)
	
		# type should be 0
		if not data.type == 0:
			print("Incorrect packet type recieved from tracker, byebye")
			return
		# return paket id from tracker is always MY assigned ID
		myID = data.id
		# info contains current network state (including what I added)
		myState = data.info
	
		# if file exists in torrentData but not in filesystem write 0 padded
		for f in myState.fileDict.keys():
			if f not in os.listdir("Shared"):
				nf = open("Shared/" + f, "w+")
				nf.write("\0"*myState.fileDict[f]["filesize"])
				nf.close()

# listen for packets on known port, respond to req packets (type=2)
def send_data(ip, port):
	global SIG_DATA
	global SIG_TIME
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.bind((ip, port))
		sock.settimeout(3) # every second check incase its time to leave
		while(True):
			sock.listen(8)
			try:
				conn, addr = sock.accept()
			except socket.timeout: # no one getting data from me for a while
				if SIG_DATA and SIG_TIME:
					return
				else:
					continue
			#print("Recieved req connection")
			with conn:
				data = conn.recv(4096)
				pak = torrentPacket.parse_tcp_data(data)
				#print("Recieved req data")
				if not pak.type == 2:
					continue
				#get first filename and first chunk
				filename = list(pak.info.fileDict.keys())[0]
				chunk = 0
				for c in pak.info.fileDict[filename]["chunkDict"].keys():
					if len(pak.info.fileDict[filename]["chunkDict"][c]) > 0:
						chunk = c
						break
				#print("Recieved req for " + filename + " " + str(c))
				# send chunk from filename
				f = open("Shared/" + filename, "rb")
				f.seek(chunk* torrentData.CHUNK_SIZE)
				chars = f.read(torrentData.CHUNK_SIZE)
				f.close()
				toSend = torrentPacket.create_data(myID, filename, chunk, chars).get_tcp_data()
				#print(toSend)
				conn.sendall(toSend)

# look for missing chunk and send req to peer
def get_data():
	global SIG_TIME
	global SIG_DATA
	while(True):
		finished = True # accumulate finised state
		# look through files for chunk that I do not have, find associated peer and try to connect
		for f in myState.fileDict.keys():
			for c in myState.fileDict[f]["chunkDict"]:
				if not myID in myState.fileDict[f]["chunkDict"][c]:
					# connect to random(?) peer who knows this chunk
					finished = False
					#print("I need " + f + " " + str(c))
					for p in myState.fileDict[f]["chunkDict"][c]:
						with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
							sock.settimeout(1) # if failed to connect try someone else
							#print("making req to " + myState.peerDict[p][0] + " " + str(myState.peerDict[p][1]))
							try:
								sock.connect((myState.peerDict[p][0], myState.peerDict[p][1]))
							except: # peer busy try another
								continue;
							# send req
							sock.sendall(torrentPacket.create_req(myID, f, c).get_tcp_data())
							#print("waiting for resp")
							data = sock.recv(4096)
							pak = torrentPacket.parse_tcp_data(data)
							# get data and write
							#print(pak.data)
							fd = open("Shared/" + f, "r+b")
							fd.seek(c * torrentData.CHUNK_SIZE)
							fd.write(pak.data)
							fd.close()
							# update self data then update tracker
							myState.peerAquireFileChunk(myID, f, c)
							update_tracker()
							sock.close()
							break # to next chunk
					# else I have this chunk so try next
			# if i have all chunks of all files & SIG_TIME then set SIG_DATA & exit
			if finished == True and SIG_TIME == True:
				SIG_DATA = True
				return

#init update gets init state of the networka dn sets my ID
update_tracker()

THREAD_LIST = []

#open socket that accepts peer connections and responds to data req's
THREAD_LIST.append( threading.Thread(target=send_data, args=(myState.peerDict[myID][0], myState.peerDict[myID][1])))
THREAD_LIST[-1].start()

#open socket that tries to connect to peers (does not block try next), sends req to peer and writes response
THREAD_LIST.append( threading.Thread(target=get_data))
THREAD_LIST[-1].start()

# main thrad wait for time
time.sleep(MIN_TIME)
# on wait sig that time is ready
SIG_TIME = True
# wait for threads to join (always get_data (-1) first)
THREAD_LIST[-1].join()
THREAD_LIST[-2].join()


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as d:
	d.connect((IP, PORT))
	
	d.sendall(torrentPacket.create_eot(myID, len(myState.fileDict.keys()) - sf).get_tcp_data())
	print("PEER " + str(myID) + " SHUTDOWN: HAS " + str(len(myState.fileDict.keys())))
	for f in myState.fileDict.keys():
		print(str(myID) + "    " + f)

