#!/usr/bin/python
import socket
import sys
import os
import time
from torrentData import torrentData
from torrentPacket import torrentPacket

IP = "127.0.0.1"
STATIC_PORT=5000
f=open("port.txt", "w+")
f.write(str(STATIC_PORT))
f.close()

netState = torrentData()

# I am ID 0
ID_COUNT = 1;

# accept connections from peers
# peer says its joining with files/chunks -> return ID & file/chunk availability
# 	peer can make p2p connections itself (check for dropped connections)
# peer asks for update -> return ID & file/chunk availability
# peer asks to leave -> erase from dicts
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
	s.bind((IP, STATIC_PORT))

	while True:
		s.listen()
		try:
			conn, addr = s.accept()
		except:
			print("Connection machine broke, have a nice day.")
			exit()
		with conn:
			data = conn.recv(65536)
			if not data:
				print('Bad Connection')
				continue
			
			# addr contains connection info
			# data contains packet class with all info
			pak = torrentPacket.parse_tcp_data(data)

			#info packet
			if pak.type == 0:
				# new client or existing peer updating? ID?
				if pak.id == -1:
					print("PEER " + str(ID_COUNT) + " CONNECT: OFFERS " + str(len(pak.info.fileDict.keys())))
					netState.addPeer(ID_COUNT, addr[0], addr[1])
					# add new peer files and give ownership under new ID
					for f in pak.info.fileDict.keys():
						print(str(ID_COUNT) + "    " + f + " " + str(pak.info.fileDict[f]["totalchunks"]))
						netState.addFile(f, pak.info.fileDict[f]["filesize"])
						netState.peerAquireWholeFile(ID_COUNT, f)
					pak.id = ID_COUNT
					ID_COUNT += 1
				else:
					# else just existing peer updating
					# new peer has pak.sender_id as -1, ID_COUNT is id
					# old peer has pak.sendeR_id as id, ID_COUNT irellevant
	
					# update self with peer's owned chunks 
					# if not new sender then print aquires
					for f in pak.info.fileDict.keys():
						# this should never return true... always should have been added above
						netState.addFile(f, pak.info.fileDict[f]["filesize"])
						for c in pak.info.fileDict[f]["chunkDict"].keys():
							# list each owned chunk if owned by peer
							if pak.id in pak.info.fileDict[f]["chunkDict"][c]:
								if netState.peerAquireFileChunk(pak.id, f, c):
									print("PEER " + str(pak.id) + " ACQUIRED: CHUNK " + str(c+1) + "/" + str(pak.info.fileDict[f]["totalchunks"]) + " " + f)

				# send peer entire list of chunk data
				# sender_id is overloaded to be THEIR sender_id
				conn.sendall(torrentPacket.create_info(pak.id, netState).get_tcp_data())
			#eot
			elif pak.type == 1:
				# peer must have checked if they should leave
				print("PEER " + str(pak.id) + " DISCONNECT: RECEIVED " + str(pak.data[0]))
				for f in pak.info.fileDict.keys():
					print(str(pak.id) + "    " + f)
				netState.removePeer(pak.id)
			# tracker does not deal with data packets
