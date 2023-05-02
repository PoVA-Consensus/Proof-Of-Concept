import hashlib
import json
from web3 import Web3
import datetime as _dt
import requests
import argparse
import logging
import datetime
import os
import ast

# Set the logging level to debug
class ColourLogs(logging.Formatter):
    grey = '\x1b[38;21m'
    green = '\033[92m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'
    blue = '\033[34m'

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.blue + self.fmt + self.reset,
            logging.INFO: self.green + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Define format for logs
fmt = '%(asctime)s | %(levelname)8s | %(message)s'

# Create stdout handler for logging to the console (logs all five levels)
stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(ColourLogs(fmt))

# Create file handler for logging to a file (logs all five levels)
today = datetime.date.today()
file_handler = logging.FileHandler('logs/blockchain_{}.log'.format(today.strftime('%Y_%m_%d')))
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(fmt))

# Add both handlers to the logger
logger.addHandler(stdout_handler)
logger.addHandler(file_handler)

class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps(
        {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
        }, 
        sort_keys=True).encode() 

        return hashlib.sha256(block_string).hexdigest()

    def display_block(obj):
        block_json = json.dumps(obj.__dict__, default=dict)
        return block_json

nodes = {}
authority_nodes = {}
authority_count = 0
candidate_count = 0
current_primary = None
AUTHORITY_THRESHOLD = 1000
primary_index = 0
BLOCK_REWARD = 100
PENALTY = 250
MIN_TRANSACTION_RATIO = 2
VERIFY_URL = "http://127.0.0.1:5000/verify-certificate"
CA_CHAIN_URL = "http://127.0.0.1:8200/v1/pki/ca_chain"

class Node:
    def __init__(self):
        self.is_authority = False
        self.is_full_node = False
        self.reputation = 0
        self.authority_index = -1
        self.certificate = bytes()
        self.device_id = 0b0 * 160
    
    def display_node(obj):
        node_json = json.dumps(obj.__dict__, default=dict)
        return node_json
    
    def add_node(self, nodes, candidate_count,  is_full_node, certificate, device_id, authority_result):
        if self.reputation != 0:
            raise Exception("Node already added")
        self.is_full_node = is_full_node
        self.reputation = AUTHORITY_THRESHOLD
        self.certificate = certificate
        self.device_id = device_id
        candidate_count = candidate_count + 1
        
        votes = 0
        node_indices = []
        for node_id, node_data in nodes.items():

            if node_data["is_full_node"]:
                chain_response = requests.get(CA_CHAIN_URL)
                logger.info(f"Node {node_id} has retrieved the CA chain")
                # print(chain_response.text)
                verify_response = requests.post(VERIFY_URL, data={"certificate": cert_data, "trusted": chain_response.text})

                # Check if the response was successful
                if verify_response.text == "True":
                    logger.info(f"Node {node_id} has verified the certificate. Response: The certificate is valid")
                    votes+=1
                    if authority_result == verify_response.text:
                        logger.debug(f"Node {node_id} result in consensus with authority node") 
                        node_indices.append(node_id)
                else:
                    logger.warning(f"Node {node_id} has verified the certificate. Response: The certificate is invalid")

            else:
                logger.warning(f"Node {node_id} could not verify due to timeout. Not full node.")

        if self.check_votes(votes, nodes) and len(node_indices) != 0:
            # print(type(json.loads(self.display_node())))
            nodes[len(nodes)] = json.loads(self.display_node())
            logger.info(f"Device with device ID {device_id} added to the network")
            self.reward_nodes(nodes, node_indices)
        else:
            logger.info("Node cannot be added as majority vote not attained")

    def check_votes(self, votes, nodes):
        if votes > len(nodes)//2:
            return True
        return False
    
    def reward_nodes(self, nodes, indices):
        for index in indices:
            # logger.debug((nodes[index])['reputation'])
            nodes[index]['reputation'] += BLOCK_REWARD
        logger.debug("The nodes that are in consensus with the Primary node have been rewarded")
    
    def penalize_primary(nodes, index):
        nodes[index]['reputation'] = nodes[index]['reputation'] - PENALTY
        logger.info("The Authority node has been penalized")
        if nodes[index]['reputation'] < AUTHORITY_THRESHOLD :
            nodes.pop(index)
            logger.info("The Authority Node has fell below the threshold and has been removed from the network")

        
def get_authority():
    if not os.path.exists('index.txt'):
        return 0
    with open('index.txt', 'r') as f:
        return int(f.read().strip())
    
def set_authority(index):
    with open('index.txt', 'w') as f:
        f.write(str(index))

def authority_verify(index, cert_data):
    chain_response = requests.get(CA_CHAIN_URL)
    logger.info(f"Authority node {index} is the primary node")
    logger.info(f"Authority node {index} has retrieved the CA chain")
    # print(chain_response.text)
    verify_response = requests.post(VERIFY_URL, data={"certificate": cert_data, "trusted": chain_response.text})
    # logger.info(verify_response.text)
    return verify_response.text


genesis_block = Block(0,  str(_dt.datetime.now()), "Genesis Block",0)

block_exists = {}
block_hashes = {}
block_parents = {}
block_lengths = {}
last_block = genesis_block
block_exists[genesis_block.hash] = True
block_hashes[0] = genesis_block.hash

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This simulates the Proof of Concept for the blockchain with Proof of Verified Authority Consensus')

    parser.add_argument('--method', type=str, choices=['add', 'remove', 'viewnode'], help='This argument facilitates choosing the action on a node')
    parser.add_argument('--certificate', type=str, help='The argument enables you to specify the path to the device certificate file')
    parser.add_argument('--fullnode', action='store_true', help='This is a flag to indicate if the device is a full node')
    parser.add_argument('--deviceid', type=str, help='This argument specifies the device ID')
    parser.add_argument('--node', type=int, help='This argument specifies the node index for the viewnode method')

    # parse arguments
    args = parser.parse_args()

    # access values of arguments
    method = args.method

    nodes = {
            0: {"is_authority": False, "is_full_node": True, "reputation": 1000, "authority_index": -1, "certificate": "cert", "device_id": 49},
            1: {"is_authority": True, "is_full_node": False, "reputation": 500, "authority_index": 0, "certificate": "cert", "device_id": 44},
            2: {"is_authority": False, "is_full_node": True, "reputation": 750, "authority_index": -1, "certificate": "cert", "device_id": 45},
            3: {"is_authority": True, "is_full_node": True, "reputation": 1500, "authority_index": 1, "certificate": "cert", "device_id": 54},
            }

    if method == 'add':

        certificate_path = args.certificate        
        full_node = args.fullnode
        device_id = args.deviceid
        missing_args = [arg_name for arg_name, arg_value in 
                        [('certificate_path', certificate_path), ('full_node', full_node), ('device_id', device_id)] 
                        if arg_value is None]
        if missing_args:
            logger.error("Error: The following arguments are missing:%s", ' '.join(missing_args))
            exit(1)
        
        with open(certificate_path, "r") as cert_file:
                cert_data = cert_file.read()

        node = Node()
                
        authority_nodes = [44, 54]
        primary_index = get_authority() % len(authority_nodes)
        # print(primary_index)
        set_authority(primary_index + 1)
        authority_result = authority_verify(primary_index, cert_data)
        
        try:
            node.add_node(nodes, candidate_count, full_node, cert_data, device_id, authority_result)
            # logger.info(node.display_node())
        except Exception as e:
            logger.error(e)
    
    elif method == 'viewnode':
        node_num = args.node
        logger.info(json.dumps(nodes[node_num], indent=4))
    # print(nodes)
    # print(block_hashes)