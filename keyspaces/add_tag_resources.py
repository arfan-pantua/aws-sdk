import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
def list_keyspaces(self, limit):
    """
    Lists the keyspaces in your account.

    :param limit: The maximum number of keyspaces to list.
    """
    try:
        ks_paginator = self.get_paginator("list_keyspaces")
        except_ks = ["system","system_schema", "system_schema_mcs", "system_multiregion_info"]
        for page in ks_paginator.paginate(PaginationConfig={"MaxItems": limit}):
            for ks in page["keyspaces"]:
                self.ks_name = ks["keyspaceName"]
                print("KS nya : "+ks["keyspaceName"])
                if self.ks_name not in except_ks:
                    list_tables(self)
                # print(ks["keyspaceName"])
                # print(f"\t{ks['resourceArn']}")
    except ClientError as err:
        logger.error(
            "Couldn't list keyspaces. Here's why: %s: %s",
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise

def list_tables(self):
    """
    Lists the tables in the keyspace.
    """
    try:
        table_paginator = self.get_paginator("list_tables")
        for page in table_paginator.paginate(keyspaceName=self.ks_name):
            for table in page["tables"]:
                print("Table : "+table["tableName"])
                print(f"\t{table['resourceArn']}")
                self.arn = table['resourceArn']
                tagResource(self)
    except ClientError as err:
        logger.error(
            "Couldn't list tables in keyspace %s. Here's why: %s: %s",
            self.ks_name,
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise

def tagResource(client):
    # list_keyspaces(client,10)
    response = client.tag_resource(
        resourceArn=client.arn,
        tags=[
            {
                'key': 'Keyspace',
                'value': client.ks_name
            },
        ]
    )

if __name__ == "__main__":
    list_keyspaces(boto3.client("keyspaces"),10)