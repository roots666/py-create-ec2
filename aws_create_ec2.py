#!/usr/bin/env python3

import argparse
import boto3
import os
from operator import itemgetter

parser = argparse.ArgumentParser()

parser.add_argument('-r','--region', action='store', dest='region', type=str,
                    help='AWS Region. Use like: -r ap-southeast-1', default='us-east-1')
parser.add_argument('-a','--ami', action='store', dest='ami_filter', type=str,
                    help='AWS AMI. Use like: -a amzn2-ami-hvm-2.0.????????-x86_64-gp2', default='amzn2-ami-hvm-2.0.????????-x86_64-gp2')
parser.add_argument('-t','--type', action='store', dest='type', type=str,
                    help='AWS instance type. Use like: -t t2.nano', default='t2.micro')
parser.add_argument('-n','--num', action='store', dest='num', type=int,
                    help='number of ec2 instances. Use like: -n 2', default=1)
arg = parser.parse_args()

# variables
aws_region = arg.region
aws_az1 = arg.region + "a"
aws_az2 = arg.region + "b"
vpc_cidr = "10.0.0.0/16"
public_subnet_cidr = "10.0.1.0/24"
private_subnet_cidr = "10.0.2.0/24"
source_cidr = '0.0.0.0/0'
fp = open('userdata.txt')
user_data_content = fp.read()

#initialize boto3 ec2 client and resource
ec2_resource = boto3.resource('ec2', aws_region)
ec2_client = boto3.client('ec2', aws_region)
 
#-------------------Create-VPC-------------------------------
vpc = ec2_resource.create_vpc(CidrBlock=vpc_cidr)
vpc.wait_until_available()
print('VPC created successfully with VPC ID: ' + vpc.id)
 
# modify vpc to enable dns hostname
vpc.modify_attribute(EnableDnsHostnames={'Value':True})

#--------------------Create-Subnets---------------------------
# create public subnet
public_subnet = vpc.create_subnet(AvailabilityZone=aws_az1,CidrBlock=public_subnet_cidr)
ec2_client.modify_subnet_attribute(MapPublicIpOnLaunch={'Value': True},SubnetId=public_subnet.id)
print('Public Subnet created successfully with SUBNET ID: ' + public_subnet.id)
 
# create a private subnet
private_subnet = vpc.create_subnet(AvailabilityZone=aws_az2,CidrBlock=private_subnet_cidr)
print('Private Subnet created successfully with SUBNET ID: ' + private_subnet.id)

#-------------------InternetGateway-------------------------
# create an internet gateway and attach to the vpc
internet_gateway = ec2_resource.create_internet_gateway()
internet_gateway.attach_to_vpc(VpcId=vpc.id)
print('Internet Gateway created successfully with GATEWAY ID: ' + internet_gateway.id)

#---------------------RouteTable------------------------------
# create a public route table and assosiate to public subnet
public_route_table = ec2_resource.create_route_table(VpcId=vpc.id)
public_route_table.associate_with_subnet(SubnetId=public_subnet.id)

# create route to Internet Gateway in public route table
public_route = ec2_client.create_route(RouteTableId=public_route_table.id,DestinationCidrBlock=source_cidr,GatewayId=internet_gateway.id)
print('Public Route Table with ID ' + public_route_table.id + ' created successfully')
 
# create a private route table and assosiate to private subnet
private_route_table = ec2_resource.create_route_table(VpcId=vpc.id)
private_route_table.associate_with_subnet(SubnetId=private_subnet.id)
print('Private Route Table with ID ' + private_route_table.id + ' created successfully')

#------------------Create-SecurityGroup---------------------------
# create a security group
security_group = ec2_resource.create_security_group(GroupName='myvpc_security_group',Description='Used by Me',VpcId= vpc.id)
 
# create ssh ingress rules
ec2_client.authorize_security_group_ingress(GroupId=security_group.id,IpProtocol='tcp',FromPort=22,ToPort=22,CidrIp=source_cidr)
print('Security Group with ID ' + security_group.id + ' created successfully')
 
# get the latest AMI ID for Amazon Linux 2
ec2_ami_ids = ec2_client.describe_images(
    Filters=[{'Name':'name','Values':[arg.ami_filter]},{'Name':'state','Values':['available']}],
    Owners=['amazon']
)
image_details = sorted(ec2_ami_ids['Images'],key=itemgetter('CreationDate'),reverse=True)
ec2_ami_id = image_details[0]['ImageId']
 
# create a key pair
try:
    outfile = open('my_keypair.pem','w')
except IOError as e:
    print(u'IOError')
else:
    keypair = ec2_client.create_key_pair(KeyName='my_keypair')
    keyval = keypair['KeyMaterial']
    outfile.write(keyval)
    outfile.close()
    os.chmod('my_keypair.pem', 400)
    print('Key Pair my_keypair created successfully')

# create tags
vpc.create_tags(Tags=[{"Key": "Name", "Value": "myvpc"}])
public_subnet.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_public_subnet"}])
private_subnet.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_private_subnet"}])
internet_gateway.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_internet_gateway"}])
public_route_table.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_public_route_table"}])
private_route_table.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_private_route_table"}])
security_group.create_tags(Tags=[{"Key": "Name", "Value": "myvpc_security_group"}])

#--------------------Create-Ec2-Instance---------------------------
# create an ec2 instance
def ec2_instance_create():
    ec2_instance = ec2_resource.create_instances(
        ImageId=ec2_ami_id,
        InstanceType=arg.type,
        KeyName='my_keypair',
        Monitoring={'Enabled':False},
        SecurityGroupIds=[security_group.id],
        SubnetId=public_subnet.id,
        UserData=user_data_content,
        MaxCount=1,
        MinCount=1,
        #PrivateIpAddress='10.0.1.10'
    )
    ec2_instance_id = ec2_instance[0].id
    print('Creating EC2 instance')
    
    #wait untill the ec2 is running
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[ec2_instance_id])
    print('EC2 Instance created successfully with ID: ' + ec2_instance_id)
    
    ec2_client.create_tags(Resources=[ec2_instance_id], Tags=[{'Key': 'Name','Value': 'myvpc_ec2_instance'}])
    
    # print instance dns name
    ec2_instance = ec2_client.describe_instances(
        Filters=[{'Name': 'tag:Name','Values': ['myvpc_ec2_instance']},
        {'Name': 'instance-state-name','Values': ['running']}]
    )
    ec2_public_dns_name = ec2_instance["Reservations"][0]["Instances"][0]["PublicDnsName"]
    print('instance URL: ' + ec2_public_dns_name)

if __name__ == '__main__':
    for _ in range(arg.num):
        ec2_instance_create()