#!/bin/bash
cd /home/ubuntu/A2/ece1779A2/ManagerUI
source venv/bin/activate
python app/autoscale.py >> autoscale.log
