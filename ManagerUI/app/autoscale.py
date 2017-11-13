import boto3
import json
import threading
import time
import config
import mysql.connector
from datetime import datetime, timedelta

def get_instances_cpu_avg():

    # Open DB Connection
    cnx    = mysql.connector.connect(user=config.DB_USER, password=config.DB_PASS, host=config.DB_HOST, database=config.DB_NAME)
    cursor = cnx.cursor()
                                                                                                                                 
    # Query DB for Autoscale settings
    cursor.execute("SELECT scale,upper_bound,lower_bound,scale_up,scale_down FROM autoscale WHERE id = 1")   
    auto_scale_data = cursor.fetchall()
                                                                                                                                 
    if (len(auto_scale_data) == 0):
        print ("Database is missing autoscale data")
        return False
                                                                                                                                 
    for scale,upper_bound,lower_bound,scale_up,scale_down in auto_scale_data:
        AUTO_SCALE       = scale
        AUTO_UPPER_BOUND = upper_bound
        AUTO_LOWER_BOUND = lower_bound
        AUTO_SCALE_UP    = scale_up
        AUTO_SCALE_DOWN  = scale_down
 
    print ("AUTO PARAMS: %s %s %s %s %s" % (AUTO_SCALE,AUTO_UPPER_BOUND,AUTO_LOWER_BOUND,AUTO_SCALE_UP,AUTO_SCALE_DOWN))                                                                                                                                
    # Close DB Connection
    cursor.close()
    cnx.close()

    # Create EC2 Resource
    ec2 = boto3.resource('ec2',aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)

    # Get All EC2 Instances
    instances = ec2.instances.all()

    # Test CloudWatch avgs
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
    
    sum_avg = 0
    for avg in avgs:
        sum_avg = sum_avg + avg
    
    if (n_instances):
        instances_average = sum_avg/n_instances
    else:
        instances_average = 0
    print("cpu utilization avg:%f" % (instances_average))

    if (AUTO_SCALE == 'ON'):
        if (instances_average >= AUTO_UPPER_BOUND):
            print ("CPU Average is greather than threshold.")
            print ("Increasing nodes from %d to %f" %(n_instances,n_instances*AUTO_SCALE_UP))
            increase_worker_nodes(int(n_instances*AUTO_SCALE_UP)-n_instances)
        elif (instances_average <= AUTO_LOWER_BOUND):
            print ("CPU Average is lower than threshold.")
            print ("Decreasing nodes from %d to %d" %(n_instances,max(int(n_instances/AUTO_SCALE_DOWN),1)))
            decrease_worker_nodes(n_instances - max(int(n_instances/AUTO_SCALE_DOWN),1))
        else:
            print ("CPU Average is within operating window. Total Workers %d" %(n_instances))

def increase_worker_nodes(add_instances):
    aws_session = boto3.Session(aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    ec2 = aws_session.resource('ec2')

    new_instances = ec2.create_instances(ImageId=config.EC2_ami_id,
                                         MinCount=add_instances,
                                         MaxCount=add_instances,
                                         UserData=config.EC2_user_data,
                                         InstanceType=config.EC2_instance_type,
                                         KeyName=config.EC2_key_name,
                                         SubnetId=config.EC2_subnet_id,
                                         SecurityGroupIds=config.EC2_security_group_ids,
                                         Monitoring={'Enabled': config.EC2_monitoring},
                                         TagSpecifications=[{'ResourceType': 'instance', 'Tags': [
                                             {'Key': config.EC2_tagkey, 'Value': config.EC2_tagvalue}, ]}, ])

    for instance in new_instances:
        elb_add_instance(instance.id)  # Add New Instance to ELB

    return 'OK'

def decrease_worker_nodes(delete_instances):

    if (delete_instances == 0):
        print ("Cant delete anymore")
        return

    print ("Going to delete %d" % (delete_instances))

    # Create EC2 Resource
    ec2 = boto3.resource('ec2', aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)

    # Get All EC2 Instances
    instances = ec2.instances.all()

    # Test CloudWatch avgs
    instances_ids = []
    for instance in instances:
        if ((instance.tags[0]['Value'] == 'A2WorkerNode') and (
            (instance.state['Name'] != 'terminated') and (instance.state['Name'] != 'shutting-down'))):
            instances_ids.append(instance.id)

    avgs = []
    n_instances = 0

    # Get minute avg CPU utilization for every worker instance
    for id in instances_ids:
        instance = ec2.Instance(id)
        client = boto3.client('cloudwatch', aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
        metric_name = 'CPUUtilization'
        namespace = 'AWS/EC2'
        statistic = 'Average'  # could be Sum,Maximum,Minimum,SampleCount,Average

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
            data = datapoints[0]
            average = data["Average"]
            avgs.append(average)
        n_instances = n_instances + 1

    print ("Instances:")
    print (instances_ids)
    print ("Averages:")
    print (avgs)

    # Sort Instances by CPU Averages in Non-Increasing order
    X = instances_ids
    Y = avgs

    Z = [x for _, x in sorted(zip(Y, X))]
    print("Sorted:")
    print(Z)

    # Delete Necessary Instances by Non-Increasing CPU Average orrder
    for i in range (0,delete_instances):
        del_instances = ec2.instances.filter(InstanceIds=[Z[i]])
        for instance in del_instances:
            elb_remove_instance(instance.id) # Remove Instance from ELB
            instance.terminate()             # Terminate Instance

def elb_add_instance(instanceId):

    elbList = boto3.client('elb',aws_access_key_id=config.AWS_KEY,aws_secret_access_key=config.AWS_SECRET)
    ec2 = boto3.resource('ec2',aws_access_key_id=config.AWS_KEY,aws_secret_access_key=config.AWS_SECRET)

    elbs = elbList.describe_load_balancers()
    for elb in elbs['LoadBalancerDescriptions']:
        elb_mananger = elb

    # Adding instances to ELB:
    response = elbList.register_instances_with_load_balancer(
        LoadBalancerName='A2LB',
        Instances=[
            {
                'InstanceId': instanceId
            },
        ]
    )
    print(response)


def elb_remove_instance(instanceId):

    elbList = boto3.client('elb', aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)

    elbs = elbList.describe_load_balancers()
    for elb in elbs['LoadBalancerDescriptions']:
        elb_mananger = elb

    # Removing instance from ELB:
    response = elbList.deregister_instances_from_load_balancer(
        LoadBalancerName='A2LB',
        Instances=[
            {
                'InstanceId':  instanceId
            },
        ]
    )
    print(response)

#EXECUTE AUTOSCALE
get_instances_cpu_avg()
