import boto3
import os

def lambda_handler(event, context):
    # Get instance ID from environment variable
    instance_id = os.environ.get('INSTANCE_ID')
    if not instance_id:
        raise ValueError("INSTANCE_ID environment variable is not set")
    
    # Create EC2 client
    ec2 = boto3.client('ec2')
    
    try:
        # Start the instance
        response = ec2.start_instances(InstanceIds=[instance_id])
        
        # Get the current state
        state = response['StartingInstances'][0]['CurrentState']['Name']
        
        return {
            'statusCode': 200,
            'body': f'Successfully started instance {instance_id}. Current state: {state}'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error starting instance: {str(e)}'
        } 