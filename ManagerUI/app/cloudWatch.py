import boto3
import json
import threading
import time
from app import config
from datetime import datetime, timedelta

def get_instances_cpu_avg():

    while (True):
        
        # Create EC2 Resource
        ec2 = boto3.resource('ec2',aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)

	# Get All EC2 Instances
        instances = ec2.instances.all()

        # Test CloudWatch avgs
        instances_ids = []
        for instance in instances:
            if ((instance.tags[0]['Value'] == 'A2WorkerNode') and (instance.state['Name'] != 'terminated')):
                instances_ids.append(instance.id)

        avgs = []
        n_instances = 0

        #Get minute avg CPU utilization for every worker instance
        for id in instances_ids:
            instance    = ec2.Instance(id)
            client      = boto3.client('cloudwatch',aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
            metric_name = 'CPUUtilization'
            namespace   = 'AWS/EC2'
            statistic   = 'Average'  # could be Sum,Maximum,Minimum,SampleCount,Average

            cpu = client.get_metric_statistics(
                Period=1 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=1 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
                MetricName=metric_name,
                Namespace=namespace,  # Unit='Percent',
                Statistics=[statistic],
                Dimensions=[{'Name': 'InstanceId', 'Value': id}]
            )

            datapoints = cpu['Datapoints']
            if datapoints:
                data =datapoints[0]
                average = data["Average"]
                avgs.append(average)
            n_instances = n_instances + 1
        
        sum_avg = 0
        for avg in avgs:
            sum_avg = sum_avg + avg
        
        if (n_instances):
            instances_average = sum_avg/n_instances
        else:
            instances_average = 0
        print("cpu utilization avg:%f" % (instances_average))

	#FIXME Insert Autocaling CODE HERE

        time.sleep(5) #FIXME set to 60 once measurement code is accurate
