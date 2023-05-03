from flask import Flask, request
from OpenSSL import crypto
import re

app = Flask(__name__)

def verify_certificate_chain(cert_data, trusted_data):
    '''
    This function verifies if a given certificate traces to the root certificate in the chain of trust.
    Args:
        cert_data: Certificate data to be verified
        trusted_data: Trusted certificate data
    Return: bool based on verification
    '''
    certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)

    # To extract all the certificates in the chain of trust via the regex
    list_trust = re.findall("(-----BEGIN CERTIFICATE-----(.|\n)+?(?=-----END CERTIFICATE-----)+)", trusted_data)

    #Creating a certificate store and adding all the trusted certificates from the chain
    
    try:
        store = crypto.X509Store()

        for _cert in list_trust:
            # appending the footer to the certificate as that was not captured via the regex
            cert = _cert[0] + "-----END CERTIFICATE-----"
            client_certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
            store.add_cert(client_certificate)
        
        # Create a certificate context using the store and the loaded certificate
        store_ctx = crypto.X509StoreContext(store, certificate)
        
        # To verify the certificate
        # Returns None if the certificate can be validated
        store_ctx.verify_certificate()
        return True

    except Exception as e:
        print("Reason: " + str(e).title())
        return False

@app.route('/verify-certificate', methods=['POST'])
def verify_certificate():
    cert_data = request.form['certificate']
    trusted_data = request.form['trusted']
    if verify_certificate_chain(cert_data, trusted_data):
        return "True"
    else:
        return "False"

if __name__ == '__main__':
    app.run()
