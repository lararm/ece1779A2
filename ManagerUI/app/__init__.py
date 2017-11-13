from flask import Flask
from app import config

webapp = Flask(__name__)
webapp.secret_key = config.SECRET_KEY

from app import manager
from app import s3_examples
from app import main


