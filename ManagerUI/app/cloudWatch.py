import boto3
from app import config
from datetime import datetime, timedelta
import json
import threading

def get_instances_cpu_avg():
    threading.Timer(60.00, get_instances_cpu_avg).start()
    aws_session = boto3.Session(aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    # create connection to ec2
    ec2 = aws_session.resource('ec2')

    instances = ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    instances = ec2.instances.all()

    # Test CloudWatch avgs
    intances_ids = []
    for instance in instances:
        # filter db and mananger
        if (instance.id != config.DATABASE_ID and instance.id != config.MANAGER_ID):
            if ((instance.tags[0]['Value'] == 'A2WorkerNode') and (instance.state['Name'] != 'terminated')):
                intances_ids.append(instance.id)


    aws_session = boto3.Session(aws_access_key_id=config.AWS_KEY, aws_secret_access_key=config.AWS_SECRET)
    ec2 = aws_session.resource('ec2')
    avgs = []
    n_instances = 0

    #Get minute avg CPU utilization for every worker instance
    for id in intances_ids:
        instance = ec2.Instance(id)
        client = aws_session.client('cloudwatch')
        metric_name = 'CPUUtilization'

        ##    CPUUtilization, NetworkIn, NetworkOut, NetworkPacketsIn,
        #    NetworkPacketsOut, DiskWriteBytes, DiskReadBytes, DiskWriteOps,
        #    DiskReadOps, CPUCreditBalance, CPUCreditUsage, StatusCheckFailed,
        #    StatusCheckFailed_Instance, StatusCheckFailed_System

        namespace = 'AWS/EC2'
        statistic = 'Average'  # could be Sum,Maximum,Minimum,SampleCount,Average

        cpu = client.get_metric_statistics(
            Period=1 * 60,
            StartTime=datetime.utcnow() - timedelta(seconds=1 * 60),
            EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
            MetricName=metric_name,
            Namespace=namespace,  # Unit='Percent',
            Statistics=[statistic],
            Dimensions=[{'Name': 'InstanceId', 'Value': id}]
        )

        cpu_stats = []
        datapoints = cpu['Datapoints']
       # print(datapoints)
        if datapoints:
            data =datapoints[0]
            average = data["Average"]
            avgs.append(average)
        n_instances = n_instances + 1
    # print(avgs)
    # print(n_instances)
    sum_avg = 0
    for avg in avgs:
        sum_avg = sum_avg + avg

    instances_average = sum_avg/n_instances
    print("cpu utilization avg:")
    print(instances_average)

get_instances_cpu_avg()
