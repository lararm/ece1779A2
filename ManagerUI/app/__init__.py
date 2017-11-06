
from flask import Flask
from app import cloudWatch

webapp = Flask(__name__)

from app import ec2_examples
from app import s3_examples
from app import main

cloudWatch.get_instances_cpu_avg()

