# contain data for p2p network
# stores packet type enum
#	0 is info (torrentData)
#	1 is eot
#	2 is request for file data
#	3 is file data
# packet has id, type {info, reqData, sendData} fileDict class, data block 

import sys
import pickle
from torrentData import torrentData

class torrentPacket:
	def __init__(self, sender_id, type, info, data):
		if len(data) > torrentData.CHUNK_SIZE:
        		raise Exception("Data too large (max 512 char): ", len(data))

		self.id = sender_id
		self.type = type
		self.info = info	# torrentData instance
		self.data = data

	def get_tcp_data(self):
		return pickle.dumps(self)

	@staticmethod
	def create_info(sender_id, info):
		return torrentPacket(sender_id, 0, info, [])

	@staticmethod
	def create_eot(sender_id, rec): # gives state before exiting for logging
		# send empty torrentData (or send 0?)
		return torrentPacket(sender_id, 1, torrentData(), [rec])

	@staticmethod
	def create_req(sender_id, filename, chunk):
		# create fake network data with only 1 file and 1 chunk to overload info field
		# informs receiver of what to send back
		reqData = torrentData()
		reqData.addPeer(sender_id, 0, 0)
		reqData.addFile(filename, (chunk+1)*torrentData.CHUNK_SIZE)
		reqData.peerAquireFileChunk(sender_id, filename, chunk)
		return torrentPacket(sender_id, 2, reqData, [])

	@staticmethod
	def create_data(sender_id, filename, chunk, data):
		# create fake network data with only 1 file and 1 chunk to overload info field
		# informs receiver what the data pertains to
		reqData = torrentData()
		reqData.addPeer(sender_id, 0, 0)
		reqData.addFile(filename, (chunk+1)*torrentData.CHUNK_SIZE)
		reqData.peerAquireFileChunk(sender_id, filename, chunk)
		return torrentPacket(sender_id, 3, reqData, data)

	@staticmethod
	def parse_tcp_data(TCPdata):
		return pickle.loads(TCPdata)

