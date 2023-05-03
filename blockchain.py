import hashlib
import json
import time
import requests
import argparse
import logging
import datetime
import os
import random
from collections import Counter
import ast

from Colour import ColourLogs

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

import json
import hashlib
from datetime import datetime

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

    def display_block(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }

class Blockchain:
    def __init__(self, chain_file='chain.json', transaction_file='transaction.json'):
        self.chain_file = chain_file
        self.transaction_file = transaction_file

        try:
            with open(self.chain_file, 'r') as f:
                self.chain = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.chain = []
            self.create_genesis_block()

    def create_genesis_block(self):
        index = 0
        timestamp = str(datetime.now())
        data = "Genesis Block"
        previous_hash = ''

        genesis_block = Block(index, timestamp, data, previous_hash)
        self.chain.append(genesis_block.display_block())

        with open(self.chain_file, 'w') as f:
            json.dump(self.chain, f)

    def add_block(self, data):
        previous_block = self.chain[-1]
        previous_hash = previous_block['hash']
        index = previous_block['index'] + 1
        timestamp = str(datetime.now())

        new_block = Block(index, timestamp, data, previous_hash)
        if new_block.previous_hash == previous_hash:
            self.chain.append(new_block.display_block())
            with open(self.chain_file, 'w') as f:
                json.dump(self.chain, f)
            return True
        else:
            return False

    def display_chain(self):
        return self.chain


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
        """
        This function adds a new node to the network.

        Args:
            nodes (Dict): A registry that contains details of nodes that have been added to the network.
            follower_count (int): The number of follower nodes.
            is_full_node (bool): A boolean indicating whether the new node is a full node or not.
            certificate (str): The certificate of the new node.
            device_id (str): The unique identifier of the device.
            primary_index (int): The index of the primary node.

        Returns:
            bool: True if adding the node is successful else False.
        """
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
            return False

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
        return True
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

def get_authority_indices(nodes):
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

def remove_primary_entry(votes, primary_index):
    # Need this function to ensure that primary node entry is not set to false
    items = list(votes.items())
    del items[primary_index]
    return dict(items)

def network_noise_simulation(authority_indices, votes, primary_index):
    noise_ratio = round(random.uniform(0.3, 0.7), 4)
    logger.info(f"There is a network noise of {round((noise_ratio * 100), 4)}%")
    noise_threshold = len(authority_indices) * noise_ratio    # Setting a noise factor
    votes = remove_primary_entry(votes, primary_index)
    entries = list(votes.items())  # Convert the dictionary into a list of tuples
    random.shuffle(entries)  # Random shuffling
    for i in range(int(noise_threshold)):
        number, _ = entries[i]  
        votes[number] = False  
    logger.debug(f"Noised authority nodes {votes}")
    return votes

def broadcast_majority_count(votes):
    votes_counts = Counter(votes.values())
    # get the most common boolean value and its count
    most_common, count = votes_counts.most_common(1)[0]
    # calculate the percentage of the most common boolean value
    percentage = (count / len(votes)) * 100
    return most_common, percentage

def broadcast_authority(authority_indices, primary_index):
    votes = {}
    for authority in authority_indices:
        votes[authority] = True
    votes = network_noise_simulation(authority_indices, votes, primary_index)
    consensus_vote, vote_percent = broadcast_majority_count(votes)
    logger.info(f"Consensus vote is {consensus_vote}")
    votes[authority_indices[primary_index]] = True
    logger.debug(f"After adding primary vote {votes}")
    return votes, consensus_vote, vote_percent

def broadcast_followers(nodes, primary_index, authority_nodes):
    noise_ratio = round(random.uniform(0.3, 0.7), 4)
    logger.info(f"Network noise in propagating to follower nodes {round(noise_ratio * 100, 2)}%")
    follower_nodes_votes = {}
    for node_id, node_data in nodes.items():
        if node_data["is_full_node"] and node_id != authority_nodes[primary_index] and node_data['is_authority'] != True:
            follower_nodes_votes[node_id] = True
    
    noise_threshold = len(follower_nodes_votes) * noise_ratio 
    entries = list(follower_nodes_votes.items())  
    random.shuffle(entries)  # Random shuffling
    for i in range(int(noise_threshold)):
        number, _ = entries[i]  
        follower_nodes_votes[number] = False 
    consensus_vote, vote_percent = broadcast_majority_count(follower_nodes_votes) 
    return follower_nodes_votes, consensus_vote, vote_percent

def broadcast_reward(nodes, auth_votes_map, followers_votes_map, auth_vote, authority_nodes, primary_index):
    logger.debug("Rewarding in broadcast")
    for node_id, vote in auth_votes_map.items():
        if vote == auth_vote:
            nodes[node_id]['reputation'] += BLOCK_REWARD
            
        elif vote != auth_vote:
            nodes[node_id]['reputation'] -= PENALTY
            if nodes[node_id]['reputation'] < AUTHORITY_THRESHOLD:
                nodes[node_id]['is_authority'] = False

        elif node_id == authority_nodes[primary_index] and vote != auth_vote:
            nodes[node_id]['reputation'] = nodes[node_id]['reputation'] + PRIMARY_REWARD - BLOCK_REWARD

    for node_id, vote in followers_votes_map.items():
        if vote == auth_vote:
            nodes[node_id]['reputation'] += BLOCK_REWARD
            if nodes[node_id]['reputation'] >= AUTHORITY_THRESHOLD and nodes[node_id]['promote_count'] < MAX_TRANSACTION_RATIO:
                nodes[node_id]['is_authority'] = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This simulates the Proof of Concept for the blockchain with Proof of Verified Authority Consensus')

    parser.add_argument('--method', type=str, choices=['add', 'remove', 'viewnode', 'broadcast'], help='This argument facilitates choosing the action on a node')
    parser.add_argument('--certificate', type=str, help='The argument enables you to specify the path to the device certificate file')
    parser.add_argument('--fullnode', action='store_true', help='This is a flag to indicate if the device is a full node')
    parser.add_argument('--deviceid', type=str, help='This argument specifies the device ID')
    parser.add_argument('--node', type=int, help='This argument specifies the node index for the viewnode method')
    parser.add_argument('--state', type=str, help='This argument specifies the path to payload file containing the state')

    # parse arguments
    args = parser.parse_args()

    # access values of arguments
    method = args.method

    nodes = {
            0: {"is_authority": False, "is_full_node": True, "reputation": 900, "certificate": "cert", "device_id": 49, "promote_count": 1},
            1: {"is_authority": True, "is_full_node": True, "reputation": 1200, "certificate": "cert", "device_id": 44, "promote_count": 1},
            2: {"is_authority": True, "is_full_node": True, "reputation": 1750, "certificate": "cert", "device_id": 45, "promote_count": 1},
            3: {"is_authority": True, "is_full_node": True, "reputation": 1500, "certificate": "cert", "device_id": 54, "promote_count": 1},
            4: {"is_authority": False, "is_full_node": False, "reputation": 50, "certificate": "cert", "device_id": 79, "promote_count": 0},
            5: {"is_authority": True, "is_full_node": True, "reputation": 2550, "certificate": "cert", "device_id": 99, "promote_count": 1},
            }
    authority_nodes = get_authority_indices(nodes)
    blockchain = Blockchain()

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
        logger.debug(f"Authority node device IDs {get_authority_indices(nodes)}")
        
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

    elif method == 'broadcast':
        state_path = args.state
        if state_path == None:
            logger.error("The state payload file is missing")
        try:
            with open(state_path, "r") as state_file:
                state = state_file.read()

            primary_index = get_primary() % len(authority_nodes)
            logger.debug(f"Authority Node {primary_index} has been chosen")
            set_primary(primary_index + 1)
            logger.debug(f"Indices of authority nodes are {authority_nodes}")
            auth_votes_map, auth_vote, auth_vote_percent = broadcast_authority(authority_nodes, primary_index)
            follower_votes_map, follower_vote, follower_vote_percent = broadcast_followers(nodes, primary_index, authority_nodes)
            broadcast_reward(nodes, auth_votes_map, follower_votes_map, auth_vote, authority_nodes, primary_index)
            consensus_message = {False: "reject", True:"accept"}
            logger.info(f"{round(auth_vote_percent, 2)}% are in consensus to {consensus_message[auth_vote]} the state change.")
            # print(auth_vote_percent)
            if(auth_vote_percent > 50 and auth_vote == True):
                logger.info("The transaction has been added")
                blockchain.add_block(json.loads(state))
                chain = blockchain.display_chain()
                for block in chain:
                    print(json.dumps(block, indent=4))
            else:
                logger.warning("The transaction has not been added as it was not in majority consensus")

        except Exception as e:
            logger.error(e)

    # logger.debug(json.dumps(nodes, indent=4))
