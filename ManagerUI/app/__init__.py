import threading
from threading import Thread
from flask import Flask
from app import cloudWatch

webapp = Flask(__name__)

from app import ec2_examples
from app import s3_examples
from app import main

auto_scale = Thread(target= cloudWatch.get_instances_cpu_avg)
auto_scale.start()

#athreading.Timer(60.00, cloudWatch.get_instances_cpu_avg).start()
#cloudWatch.get_instances_cpu_avg()

