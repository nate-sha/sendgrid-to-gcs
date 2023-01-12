import os
import logging
import uuid
from datetime import date
from flask import Flask, request
# Used to senitiz the input
from werkzeug.utils import secure_filename

# Google Cloud Storage
from google.cloud import storage
from google.oauth2 import service_account

# JSON Parser
from json import loads

logger = logging.getLogger(__name__)
# Set the loggin level
logging.basicConfig(level=logging.INFO)

# Initialize the Flask application
app = Flask(__name__)

# Authenticate to Google Cloud Storage using the service account key and initialize the client
# Specify the path to the service account JSON key file
service_account_key_path = './portfolio-f4237-c261b5c29c2a.json'
credentials = service_account.Credentials.from_service_account_file(
    service_account_key_path
)
storage_client = storage.Client(credentials=credentials)


# Get the environment variables
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'BUCKET_NAME')
ALLOWED_EXTENSIONS = ['csv', 'xlsx']
ALLOWED_SENDERS = set([
    os.environ.get('ALLOWED_SENDER_1', 'sender1@vendor-domain.com'),
    os.environ.get('ALLOWED_SENDER_2', 'sender2@endor-domain.com'),
    os.environ.get('ALLOWED_SENDER_3', 'sender3@endor-domain.com'), ])
DEBUG = os.environ.get('DEBUG', True)
PORT = os.environ.get('PORT', 8080)

# Helper functions


def check_file_extension(file_name, allowed_extensions=ALLOWED_EXTENSIONS):
    """The function checks if the file extension is allowed, and returns True
        if it is allowed, otherwise returns False"""
    file_extention = file_name.rsplit('.')[-1].lower()
    # Check if the file extension is allowed
    if file_extention not in allowed_extensions:
        return False
    else:
        return True


def is_allowed_sender(sender_email, allowed_senders=ALLOWED_SENDERS):
    """The function checks if the sender's email address is allowed, and returns True
        if it is allowed, otherwise returns False"""
    if sender_email.lower() not in allowed_senders:
        return False
    else:
        return True


@ app.route('/', methods=['POST'])
def parse_email_from_sendgrid_inbound_parse():
    """Parse the email attachment sent by SendGrid-Inbound-Parse
        1. Check if the file extension is allowed
        2. Check if the sender is allowed
        4. Upload the attachement to Google Cloud Storage
        5. Return a success message, status 201: Created
    """
    try:
        # 0. parse the envolope containaing the sender (From), recipient (To), Subject and attachment
        envelope = loads(request.form.get('envelope'))
        sender_address = envelope['from']
        # Using the "To" field, get the vendor name; prefix the file name
        vendor_name = envelope['to'][0].split('@')[0]
        # The email subject is the report name
        report_name = request.form.get('subject')
        # Get the file from the request, it returns a 'FileStorage' object
        attachment = request.files.get(('attachment1'))
        # Get and sanitize the filename from the attachment
        attachment_filename = secure_filename(attachment.filename)
        # Check if the file is allowed usning the file extension and the sender's email address
        if not check_file_extension(attachment_filename) or not is_allowed_sender(sender_address):
            logger.error('Not Allowed Sender or File Extension')
            return {'status': 'Erro: Not Allowed'}, 200
        # Create a unique filename prefix the vendor name, uuid, and file extension
        unique_filename = f'{report_name}-{uuid.uuid4()}.{attachment_filename.rsplit(".")[-1]}'
        # Upload the file to Google Cloud Storage
        attachment_bytes = attachment.read()
        upload_to_cloud_storage(attachment_bytes, unique_filename, vendor_name)
        return {'status': 'CREATED'}, 201
    except Exception as error:
        logger.error(error)
        return {'status': 'error'}, 200


def upload_to_cloud_storage(attachment, filename, vendor_name):
    """Uploads the attachement to the bucket."""
    # Get the bucket using the name from the environment variable
    bucket = storage_client.bucket(BUCKET_NAME)
    # Set the blob name to the file name
    # Adding today's date and vendor name to the blob name
    blob = bucket.blob(f'{date.today()}/{vendor_name.lower()}/{filename}')
    # Upload the file to the bucket
    blob.upload_from_string(attachment)


if __name__ == "__main__":
    app.run(debug=DEBUG, host="0.0.0.0",
            port=int(PORT))
