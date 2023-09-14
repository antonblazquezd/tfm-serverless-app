import json
import uuid
import os
import boto3
from datetime import datetime

# Prepare DynamoDB client
ASSETS_TABLE = os.getenv('ASSETS_TABLE', None)
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(ASSETS_TABLE)

def lambda_handler(event, context):
    route_key = f"{event['httpMethod']} {event['resource']}"

    # Set default response, override with data from DynamoDB if any
    response_body = {'Message': 'Unsupported route'}
    status_code = 400
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }

    try:
        # Get a list of all Assets
        if route_key == 'GET /assets':
            ddb_response = ddbTable.scan(Select='ALL_ATTRIBUTES')
            # return list of items instead of full DynamoDB response
            response_body = ddb_response['Items']
            status_code = 200

        # CRUD operations for a single Asset
       
        # Read an asset by ID
        if route_key == 'GET /assets/{assetId}':
            # get data from the database
            ddb_response = ddbTable.get_item(
                Key={'assetId': event['pathParameters']['assetId']}
            )
            # return single item instead of full DynamoDB response
            if 'Item' in ddb_response:
                response_body = ddb_response['Item']
            else:
                response_body = {}
            status_code = 200
            
        # Delete a asset by ID
        if route_key == 'DELETE /assets/{assetId}':
            # delete item in the database
            ddbTable.delete_item(
                Key={'assetId': event['pathParameters']['assetId']}
            )
            response_body = {}
            status_code = 200
        
        # Create a new asset 
        if route_key == 'POST /assets':
            request_json = json.loads(event['body'])
            
            # check if it has a valid body
            if not is_valid_body(request_json):
                return response(400, {'message': 'Error: Invalid body fields'})
                
            request_json['timestamp'] = datetime.now().isoformat()
            
            # generate unique id if it isn't present in the request
            if 'assetId' not in request_json:
                request_json['assetId'] = str(uuid.uuid1())
            # update the database
            ddbTable.put_item(
                Item=request_json
            )
            response_body = request_json
            status_code = 200
        
        
    except Exception as err:
        status_code = 400
        response_body = {'Error:': str(err)}
        print(str(err))
    return response(status_code, response_body, headers)

    
    
def response(status_code, body, additional_headers=None):
    headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    if additional_headers:
        headers.update(additional_headers)

    return {'statusCode': status_code, 'body': json.dumps(body), 'headers': headers}


def is_valid_body(request_json):
    try:
        return (
            request_json
            and 'symbol' in request_json
            and 'blockchain' in request_json
        )
    except (json.JSONDecodeError, KeyError):
        return False
