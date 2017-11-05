from app import config
import boto3


def elb_add_instance(instanceId):

    elbList = boto3.client('elb',aws_access_key_id=config.AWS_KEY,aws_secret_access_key=config.AWS_SECRET)
    ec2 = boto3.resource('ec2',aws_access_key_id=config.AWS_KEY,aws_secret_access_key=config.AWS_SECRET)

    elbs = elbList.describe_load_balancers()
    for elb in elbs['LoadBalancerDescriptions']:
        elb_mananger = elb
        print(
            'ELB DNS Name : ' + elb['DNSName'])

    # Adding instances to EBL:
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
        print(
            'ELB DNS Name : ' + elb['DNSName'])

    # Removing instance from EBL:
    response = elbList.deregister_instances_from_load_balancer(
        LoadBalancerName='A2LB',
        Instances=[
            {
                'InstanceId':  instanceId
            },
        ]
    )
    print(response)