# Test Cases
## Registration of a Device
### Add a device with expired/invalid certificate
The device certificate in ```test1/``` has expired and hence it is not valid.
```console
python3 blockchain.py --fullnode --method add --deviceid 34 --certificate test1/BEC452C7-B079-4C99-57CC.e48BC-B809.pem
```

### Add a device with a valid certificate from the trusted CA
The device certificate in ```test2/``` has a valid certificate.
```console
python3 blockchain.py --fullnode --method add --deviceid 83 --certificate test2/BEC452C7-B079-4C99-57CC.e48BC-B809.pem --src_nodes nodes.json
```

## Broadcast and verification
### Sending a state change
Starting a new blockchain and adding a transaction. ```payload1.json``` has the data of a state change.
```console
python3 blockchain.py --method broadcast --state states/payload_1.json --start
```
Increasing the network noise in simulation

```console
python3 blockchain.py --method broadcast --state states/payload_1.json --max_noise 0.7
```
### Adding the next transaction
```console
python3 blockchain.py --method broadcast --state states/payload_2.json
```