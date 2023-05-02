# Proof-Of-Concept
This repository contains the source code for depicting the proof of concept of the idea proposed.

Create a virtual environment
```console
virtualenv blockchain
source blockchain/bin/activate
```

Install the required libraries and packages
```console
pip install -r requirements.txt
```

Run the verification server to verify the Device certificates against the CA chain
```console
python3 app.py
```

Help menu
```console
python3 blockchain.py -h
```
```console
usage: blockchain.py [-h] [--method {add,remove,viewnode}] [--certificate CERTIFICATE]
                     [--fullnode] [--deviceid DEVICEID] [--node NODE]

This simulates the Proof of Concept for the blockchain with Proof of Verified Authority
Consensus

options:
  -h, --help            show this help message and exit
  --method {add,remove,viewnode}
                        This argument facilitates choosing the action on a node
  --certificate CERTIFICATE
                        The argument enables you to specify the path to the device
                        certificate file
  --fullnode            This is a flag to indicate if the device is a full node
  --deviceid DEVICEID   This argument specifies the device ID
  --node NODE           This argument specifies the node index for the viewnode method
```
To add a new node to the network
```console
python3 blockchain.py --fullnode --method add --deviceid 34 --certificate test/BEC452C7-B079-4C99-57CC.e48BC-B809.pem
```
```console
2023-05-03 00:12:29,130 |    DEBUG | Authority node device IDs [1, 3]
2023-05-03 00:12:29,134 |     INFO | Authority node 0 is the primary node
2023-05-03 00:12:29,134 |     INFO | Authority node 0 has retrieved the CA chain
2023-05-03 00:12:29,140 |     INFO | Verification and voting by authority nodes have begun
2023-05-03 00:12:29,143 |     INFO | Node 1 has retrieved the CA chain
2023-05-03 00:12:29,146 |     INFO | Node 1 has verified the certificate. Response: The certificate is valid
2023-05-03 00:12:29,149 |     INFO | Node 3 has retrieved the CA chain
2023-05-03 00:12:29,152 |     INFO | Node 3 has verified the certificate. Response: The certificate is valid
2023-05-03 00:12:29,155 |     INFO | Node 0 has retrieved the CA chain
2023-05-03 00:12:29,158 |     INFO | Node 0 is in consensus with authority nodes
2023-05-03 00:12:29,161 |     INFO | Node 2 has retrieved the CA chain
2023-05-03 00:12:29,164 |     INFO | Node 2 is in consensus with authority nodes
2023-05-03 00:12:29,164 |  WARNING | Node 4 could not verify due to timeout. Not full node.
2023-05-03 00:12:29,165 |     INFO | Device with device ID 34 added to the network
2023-05-03 00:12:29,165 |     INFO | Node 0 has been promoted to Authority node
2023-05-03 00:12:29,165 |     INFO | The nodes that are in consensus with the Authority nodes have been rewarded
```


