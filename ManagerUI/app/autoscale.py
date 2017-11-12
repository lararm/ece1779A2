import boto3
import json
import threading
import time
from app import config
from app import elb
from datetime import datetime, timedelta

def get_instances_cpu_avg():

    AUTO_SCALE_ON    = config.AUTO_scale_on
    AUTO_UPPER_BOUND = config.AUTO_upper_bound
    AUTO_LOWER_BOUND = config.AUTO_lower_bound
    AUTO_SCALE_UP    = config.AUTO_scale_up   
    AUTO_SCALE_DOWN  = config.AUTO_scale_down 

    while (True):
        
        # Create EC2 Resource
        ec2 = boto3.resource('ec2',aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)

	# Get All EC2 Instances
        instances = ec2.instances.all()

        # Test CloudWatch avgs
	#FIXME change tags0 to for each tag, and look for name. In case a node goes down,the tag will be empty when it tries to retrieve data. Script will crash.
        instances_ids = []
        for instance in instances:
            if ((instance.tags[0]['Value'] == 'A2WorkerNode') and ((instance.state['Name'] != 'terminated') and (instance.state['Name'] != 'shutting-down'))):
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
                Period=2 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=2 * 60),
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
        
        print ("Averages")
        print (instances_ids)

        print ("Averages")
        print (avgs)
        sum_avg = 0
        for avg in avgs:
            sum_avg = sum_avg + avg
        
        if (n_instances):
            instances_average = sum_avg/n_instances
        else:
            instances_average = 0
        print("cpu utilization avg:%f" % (instances_average))

        if (instances_average >= AUTO_UPPER_BOUND):
            print ("Over uppower limit, should increase nodes")
            print ("Nodes could go from %d to %f" %(n_instances,n_instances*AUTO_SCALE_UP))
            for new_instance in range (n_instances,int(n_instances*AUTO_SCALE_UP)):
                print ("Creating a new instance")
                increase_worker_nodes()
        elif (instances_average <= AUTO_LOWER_BOUND):
            print ("Below lower limit, should decrease nodes")
            print ("Nodes could go from %d to %f" %(n_instances,n_instances/AUTO_SCALE_DOWN))
        else:
        	print ("In the sweet spot. %d nodes active" %(n_instances))

        time.sleep(60) 

def increase_worker_nodes():
    aws_session = boto3.Session(aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    ec2 = aws_session.resource('ec2')

    new_instances = ec2.create_instances(ImageId=config.EC2_ami_id,
                                         MinCount=config.EC2_num_instances,
                                         MaxCount=config.EC2_num_instances,
                                         UserData=config.EC2_user_data,
                                         InstanceType=config.EC2_instance_type,
                                         KeyName=config.EC2_key_name,
                                         SubnetId=config.EC2_subnet_id,
                                         SecurityGroupIds=config.EC2_security_group_ids,
                                         Monitoring={'Enabled': config.EC2_monitoring},
                                         TagSpecifications=[{'ResourceType': 'instance', 'Tags': [
                                             {'Key': config.EC2_tagkey, 'Value': config.EC2_tagvalue}, ]}, ])

    for instance in new_instances:
        elb.elb_add_instance(instance.id)  # Add New Instance to ELB

    return 'OK'
