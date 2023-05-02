import hashlib
import json
import datetime as _dt
import requests
import argparse
import logging
import datetime
import os

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
follower_count = 0
current_primary = None
AUTHORITY_THRESHOLD = 1000
primary_index = 0
BLOCK_REWARD = 100
PRIMARY_REWARD = 250
PENALTY = 450
MAX_TRANSACTION_RATIO = 3
VERIFY_URL = "http://127.0.0.1:5000/verify-certificate"
CA_CHAIN_URL = "http://127.0.0.1:8200/v1/pki/ca_chain"

class Node:
    def __init__(self):
        self.is_authority = False
        self.is_full_node = False
        self.reputation = 0
        self.certificate = bytes()
        self.device_id = 0b0 * 160
        self.promote_count = 0
    
    def display_node(obj):
        node_json = json.dumps(obj.__dict__, default=dict)
        return node_json
    
    def add_node(self, nodes, follower_count,  is_full_node, certificate, device_id, primary_index):
        if self.reputation != 0:
            raise Exception("Node already added")
        
        self.is_full_node = is_full_node
        self.reputation = AUTHORITY_THRESHOLD
        self.certificate = certificate
        self.device_id = device_id
        if is_full_node:
            follower_count = follower_count + 1

        # These lists store the indices if they voted
        follower_node_indices = []
        auth_vote, authority_node_indices = authority_voting(nodes)
        
        if auth_vote == None:
            return None

        for node_id, node_data in nodes.items():

            if node_data["is_full_node"] and node_data["is_authority"] == False:
                chain_response = requests.get(CA_CHAIN_URL)
                logger.info(f"Node {node_id} has retrieved the CA chain")
                # print(chain_response.text)
                verify_response = requests.post(VERIFY_URL, data={"certificate": cert_data, "trusted": chain_response.text})

                # Check if the response was successful
                if str(auth_vote) == verify_response.text:
                    logger.info(f"Node {node_id} is in consensus with authority nodes")
                    follower_node_indices.append(node_id)
                else:
                    logger.warning(f"Node {node_id} is not in consensus with authority nodes")

            elif node_data["is_full_node"] == False:
                logger.warning(f"Node {node_id} could not verify due to timeout. Not full node.")

        if auth_vote == True :
            # print(type(json.loads(self.display_node())))
            nodes[len(nodes)] = json.loads(self.display_node())
            logger.info(f"Device with device ID {device_id} added to the network")
            
        else:
            logger.info("Node cannot be added as majority vote not attained")

        

        self.penalize_authority(nodes, authority_node_indices)
        self.reward_follower_nodes(nodes, follower_node_indices)
        
        self.update_reputation_by_authority_index(nodes, primary_index)
        # logger.debug(authority_node_indices)

    def check_votes(self, votes, all_auth_nodes):
        if votes > len(all_auth_nodes)//2:
            return True
        return False
    
    def reward_follower_nodes(self, nodes, indices):
        for index in indices:
            # logger.debug((nodes[index])['reputation'])
            nodes[index]['reputation'] += BLOCK_REWARD
            if nodes[index]['reputation'] >= AUTHORITY_THRESHOLD:
                if nodes[index]['promote_count'] < MAX_TRANSACTION_RATIO:
                    nodes[index]['is_authority'] =  True
                    nodes[index]['promote_count'] += 1
                    logger.info(f"Node {index} has been promoted to Authority node")
                else:
                    logger.warning(f"Node {index} has crossed threshold but has been promoted for more than maximum transaction limit")
        
        logger.info("The nodes that are in consensus with the Authority nodes have been rewarded")
    
    def update_reputation_by_authority_index(self, nodes, authority_index):
        for node_id, node_data in nodes.items():
            if node_id == authority_index:
                node_data["reputation"] += PRIMARY_REWARD

    def penalize_authority(self, nodes, voted_indices):
        for node_id, node_data in nodes.items():
            if node_data["is_authority"] and node_id not in voted_indices:
                node_data["reputation"] -= PENALTY
                logger.info(f"Node {node_id} is an Authority node and has been penalized: Reason: No vote in transaction")
        
def get_primary():
    if not os.path.exists('index.txt'):
        return 0
    with open('index.txt', 'r') as f:
        return int(f.read().strip())
    
def set_primary(index):
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

def get_authority_device_ids(nodes):
    return [node_id for node_id, node_data in nodes.items() if node_data["is_authority"]]


def penalize_primary(nodes, index, follower_count):
        nodes[index]['reputation'] = nodes[index]['reputation'] - PENALTY
        logger.info("The Authority node has been penalized")
        if nodes[index]['reputation'] < AUTHORITY_THRESHOLD :
            nodes.pop(index)
            logger.info("The Authority Node has fell below the threshold and has been removed from the network")
            follower_count -= 1

def authority_voting(nodes):
    authority_node_votes = {}
    votes_true = 0
    votes_false = 0
    logger.info("Verification and voting by authority nodes have begun")
    for node_id, node_data in nodes.items():

        if node_data["is_authority"]:
            chain_response = requests.get(CA_CHAIN_URL)
            logger.info(f"Node {node_id} has retrieved the CA chain")
            # print(chain_response.text)
            verify_response = requests.post(VERIFY_URL, data={"certificate": cert_data, "trusted": chain_response.text})

            # Check if the response was successful
            if verify_response.status_code == 200:
                if verify_response.text == "True":
                    logger.info(f"Node {node_id} has verified the certificate. Response: The certificate is valid")
                    votes_true += 1
                    authority_node_votes[node_id] = "True"
                else:
                    logger.warning(f"Node {node_id} has verified the certificate. Response: The certificate is invalid")
                    votes_false += 1
                    authority_node_votes[node_id] = "False"
            else:
                authority_node_votes[node_id] = "Fail"
    
    if votes_true == votes_false >= len(authority_node_votes) // 2:
        return None, []
    elif votes_true > votes_false or votes_false > votes_true:
        return votes_true > len(authority_node_votes) // 2, authority_node_votes.keys()
    return None, []           

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
            0: {"is_authority": False, "is_full_node": True, "reputation": 900, "certificate": "cert", "device_id": 49, "promote_count": 1},
            1: {"is_authority": True, "is_full_node": True, "reputation": 1200, "certificate": "cert", "device_id": 44, "promote_count": 1},
            2: {"is_authority": False, "is_full_node": True, "reputation": 750, "certificate": "cert", "device_id": 45, "promote_count": 0},
            3: {"is_authority": True, "is_full_node": True, "reputation": 1500, "certificate": "cert", "device_id": 54, "promote_count": 1},
            4: {"is_authority": False, "is_full_node": False, "reputation": 50, "certificate": "cert", "device_id": 79, "promote_count": 0},
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
        logger.debug(f"Authority node device IDs {get_authority_device_ids(nodes)}")
        authority_nodes = get_authority_device_ids(nodes)
        # print(authority_nodes)
        primary_index = get_primary() % len(authority_nodes)
        # print(primary_index)
        set_primary(primary_index + 1)
        authority_result = authority_verify(primary_index, cert_data)
        
        try:
            node.add_node(nodes, follower_count, full_node, cert_data, device_id, primary_index)
            # logger.info(node.display_node())
        except Exception as e:
            logger.error(e)
    
    elif method == 'viewnode':
        node_num = args.node
        logger.info(json.dumps(nodes[node_num], indent=4))
    # logger.debug(json.dumps(nodes, indent=4))
    # print(block_hashes)