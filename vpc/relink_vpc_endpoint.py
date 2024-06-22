import logging
import boto3
import boto3.session
import socket
import time
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
PrivateSubnet=[]
VPCEndPointName=...
TargetGroupName=...
VPCId=...
ServiceName=...
SecurityGroupIds=[...,...]
RoleName=...
RoleArn=...

def getAllPrivateSubnet(ec2):
    print("Get all private subnet IN")
    privateSubnet=[]
    responses = ec2.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    VPCId,
                ]
            },
        ]
    )
    for respon in responses["Subnets"]:
        for x in respon["Tags"]:
            if x["Key"] == "Name":
                if "private" in x["Value"]:
                    privateSubnet.append(respon["SubnetId"])
    print("Get all private subnet OUT")
    return privateSubnet

# def getRouteTable(ec2,subnetId):
#     response = ec2.describe_route_tables(
#         Filters=[
#             {
#                 'Name': 'association.subnet-id',
#                 'Values': [
#                     subnetId,
#                 ]
#             },
#         ]
#     )
#     for route in response["RouteTables"]:
#         print("Route table : " + route[""] )

def deleteVpc(ec2):
    print("Delete VPC IN")
    vpcEndPointId = getVpcEndpointId(ec2)
    ec2.delete_vpc_endpoints(
        VpcEndpointIds=[
            vpcEndPointId,
        ]
    )
    print("Delete VPC OUT")
    input("Press enter to continue...")
def createVpcEndpoint(ec2):
    print("Create VPC Endpoint IN")
    session = temp_session()
    privateSubnet=getAllPrivateSubnet(ec2)
    response = session.create_vpc_endpoint(
        ServiceName=ServiceName,
        VpcEndpointType="Interface",
        VpcId=VPCId,
        SecurityGroupIds=SecurityGroupIds,
        SubnetIds=privateSubnet,
        TagSpecifications=[
            {
                'ResourceType': 'vpc-endpoint',
                'Tags': [
                    {
                        'Key': 'hydrax.io/client',
                        'Value': 'dbspb'
                    },
                    {
                        'Key': 'hydrax.io/env',
                        'Value': 'uat'
                    },
                    {
                        'Key': 'Name',
                        'Value': VPCEndPointName                       
                    }
                ]
            },
        ]
    )
    vpceId = response["VpcEndpoint"]["VpcEndpointId"]
    getState(ec2,vpceId)
    print("Create VPC Endpoint OUT")

def getState(ec2,vpceId):    
    try:
        print("Get VPC Endpoint State IN")
        while True:
            response = ec2.describe_vpc_endpoints(
                Filters=[
                    {
                        'Name': 'vpc-endpoint-state',
                        'Values': [
                            'available',
                        ]
                    },
                    {
                        'Name': 'vpc-endpoint-id',
                        'Values': [
                            vpceId,
                        ]
                    }
                ],
            )
            if response["VpcEndpoints"] == []:
                time.sleep(10)
                print("Make sure you accepted connection in vpc endpoint service...")
                # continue
            else:
                print("VPC Endpoint " + vpceId + " is available")
                print("Get VPC Endpoint State OUT")
                break
    except ClientError as err:
            logger.error(
                "Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
    
    # while True:
    #     if response["VpcEndpoints"] != "":
    #         break
    #     time.sleep(10)

def getVpcEndpointId(ec2):
    print("Get VPC Endpoint IN")
    try:
        response = ec2.describe_vpc_endpoints(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [
                        VPCEndPointName,
                    ]
                },
            ]
        )
        for endpoint in response["VpcEndpoints"]:
            if endpoint["VpcEndpointId"] != "":
                return endpoint["VpcEndpointId"]
        print("Get VPC Endpoint OUT")
        
    except ClientError as err:
            logger.error(
                "Couldn't get Vpc Endpoint. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
 
def setNewIpAddress(ec2):
    print("Set New IP Address IN")
    VPCEndpointId=getVpcEndpointId(ec2)
    response = ec2.describe_vpc_endpoints(
        Filters=[
            {
                'Name': 'vpc-endpoint-id',
                'Values': [
                    VPCEndpointId,
                ]
            },
        ] 
    )
    for res in response["VpcEndpoints"]:
        # print(f"\n{res['DnsEntries'][0]['DnsName']}")
        for dnsName in res["DnsEntries"]:
            if dnsName["DnsName"] != "":
                DNSName = dnsName["DnsName"]
                break
            
        if DNSName != "":
            break
    addr = socket.gethostbyname_ex(DNSName)    
    ipAddress=[]
    for i in addr[2]:
        ipAddress.append(i)
    setTargetGroupIP(ipAddress)
    print("Set New IP Address OUT")

def setTargetGroupIP(newIpAddress):
    print("Set Target Group IP IN")
    elbv2 = boto3.client("elbv2")
    TargetRegisterIps = []
    TargetDeregisterIps = []
    for i in newIpAddress:
        TargetRegisterIps.append({'Id': i})
    global tgArn
    response = elbv2.describe_target_groups(
        Names=[TargetGroupName]
    )
    for tg in response["TargetGroups"]:
        tgArn = tg["TargetGroupArn"]
    responseTargetHealt = elbv2.describe_target_health(
        TargetGroupArn=tgArn
    )
    for ip in responseTargetHealt["TargetHealthDescriptions"]:
        target = ip["Target"]
        TargetDeregisterIps.append({'Id':target["Id"]})
    if len(TargetDeregisterIps) > 0:
        elbv2.deregister_targets(
            TargetGroupArn=tgArn,
            Targets=TargetDeregisterIps
        )  
    if len(TargetRegisterIps) > 0:
        elbv2.register_targets(
            TargetGroupArn=tgArn,
            Targets=TargetRegisterIps
        )
    print("Set Target Group IP OUT")

def temp_session():
    print("Temp session IN")
    session = boto3.session.Session()
    sts = session.client("sts")
    # sts = boto3.client('sts')
    response = sts.assume_role(
        RoleArn=RoleArn,
        RoleSessionName=RoleName
    )
    temp_credentials = response["Credentials"]

    session = boto3.client(
        "ec2",
        aws_access_key_id=temp_credentials["AccessKeyId"],
        aws_secret_access_key=temp_credentials["SecretAccessKey"],
        aws_session_token=temp_credentials["SessionToken"],
    )
    print("Temp session OUT")
    return session

if __name__ == "__main__":
    # deleteVpc(boto3.client("ec2"))
    createVpcEndpoint(boto3.client("ec2"))
    # setNewIpAddress(boto3.client("ec2"))
    
# https://www.learnaws.org/2022/09/30/aws-boto3-assume-role/