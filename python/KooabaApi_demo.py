import logging

from KASignature import KASignature
from KooabaApi import BasicAPIClient

# Configuration 
BUCKET_ID = '<enter bucket id>'
DATA_KEY_SECRET_TOKEN = '<enter data api token>'
QUERY_KEY_SECRET_TOKEN = '<enter query api token>' 

## only needed for KA authentication
QUERY_KEY_ID = '<enter query api key id>' 

# Use the INFO logging level and log all output to stdout (default)
logging.basicConfig(level=logging.INFO, format='%(name)s:%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

### example usage of api
def main():
    query_example()
    #upload_example()


def query_example():
    #simple example of KA signature
    signer = KASignature('aSecretKey')
    signature = signer.sign('POST', 'aBody','text/plain', 'Sun, 06 Nov 1994 08:49:37 GMT', '/v2/query')
    logger.info('generated signature: %s', signature)
    logger.info('expected signature: 6XVAzB+hA9JEFWZdg+1ssZ+gfRo=')
    
    # perform an actual request
    client = BasicAPIClient(QUERY_KEY_SECRET_TOKEN, QUERY_KEY_ID)
   
    try:
        result = client.query('../images/query_image.jpg', 'KA')
    except:
        logger.exception('Query failed')
        raise


def upload_example():

    client = BasicAPIClient(DATA_KEY_SECRET_TOKEN)

    # loading an image into memory
    data, content_type = client.data_from_file('../images/db_image.jpg')
    
    try:
       item = client.create_item(BUCKET_ID, 'aTitle', 'myRefId', '{}')
       logger.info('created item %s', item['uuid'])
       images = client.attach_image(BUCKET_ID, item['uuid'], content_type, data)
       logger.info('attached image %s', images[0]['sha1'])
    except:
       logger.exception('Upload failed')
       raise


if __name__ == '__main__':
    import sys
    sys.exit(main())

