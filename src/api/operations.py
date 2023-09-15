import json
import uuid
import os
import boto3
from datetime import datetime

# Prepare DynamoDB client
dynamodb = boto3.resource('dynamodb')

OPERATIONS_TABLE = os.getenv('OPERATIONS_TABLE', None)
WALLETS_TABLE = os.getenv('WALLETS_TABLE', None)
USERS_TABLE = os.getenv("USERS_TABLE", None)
ASSETS_TABLE = os.getenv('ASSETS_TABLE', None)


def lambda_handler(event, context):
    route_key = f"{event['httpMethod']} {event['resource']}"

    # Set default response, override with data from DynamoDB if any
    response_body = {'Message': 'Unsupported route'}
    status_code = 400
    headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    # First check if userId and walletId exist
    ddb_response_user = dynamodb.Table(USERS_TABLE).get_item(
        TableName= USERS_TABLE,
        Key={'userId': event['pathParameters']['userId']}
    )
    if 'Item' not in ddb_response_user:
        return response(400, { 'Error': "User not found"})
    
    ddb_response_wallet = dynamodb.Table(WALLETS_TABLE).get_item(
        TableName= WALLETS_TABLE,
        Key={'walletId': event['pathParameters']['walletId']}
    )
    if 'Item' not in ddb_response_wallet:
        return response(400, { 'Error': "Wallet not found"})
    

    try:
        # Get a list of all Operations
        if route_key == 'GET /users/{userId}/wallets/{walletId}/operations':
            
            try:
                ddb_response = dynamodb.Table(OPERATIONS_TABLE).scan(
                    TableName= OPERATIONS_TABLE,
                    FilterExpression='walletId = :id',
                    ExpressionAttributeValues={
                        ':id': event['pathParameters']['walletId']
                    },
                    IndexName= 'Operations-WalletIndex',
                )
                # return list of items instead of full DynamoDB response
                response_body = ddb_response['Items']
                status_code = 200
            except Exception as err:
                status_code = 400
                response_body = {'Error:': str(err)}
                print(str(err))

        # CRUD operations for a single Operation

        # Read a operation by ID
        if route_key == 'GET /users/{userId}/wallets/{walletId}/operations/{operationId}':
            # get data from the database
            ddb_response = dynamodb.Table(WALLETS_TABLE).get_item(
                TableName= WALLETS_TABLE,
                Key={'walletId': event['pathParameters']['walletId']}
            )
            
            # return single item instead of full DynamoDB response
            if 'Item' in ddb_response and ddb_response['Item']['userId'] == event['pathParameters']['userId']:
                response_body = ddb_response['Item']
            else:
                response_body = {}
            status_code = 200

        # Delete a operation by ID
        if route_key == 'DELETE /users/{userId}/wallets/{walletId}/operations/{operationId}':
            # check if wallet is valid
            wallet = get_wallet_by_id(event['pathParameters']['walletId'])
            if not wallet:
                return response(400, {'message': 'Error: Wallet not found'})

            # check if userId is valid
            if wallet['userId'] != event['pathParameters']['userId']:
                return response(400, {'message': 'Error: Invalid userId'})

            # delete item in the database
            dynamodb.Table(WALLETS_TABLE).delete_item(
                TableName= WALLETS_TABLE,
                Key={'walletId': event['pathParameters']['walletId']}
            )
            response_body = {}
            status_code = 200

        # Create a new operation
        if route_key == 'POST /users/{userId}/wallets/{walletId}/operations':
            request_json = json.loads(event['body'])

            # check if it has a valid body
            if not is_valid_body(request_json):
                return response(400, {'message': 'Error: Invalid body fields'})

            # check if the wallet belongs to the user
            if not ddb_response_wallet['Item']['walletId'] == ddb_response_user['Item']['walletId']:
                return response(400, { 'Error': "Wallet does not belong to the user"})

            request_json['walletId'] = event['pathParameters']['walletId']

            # generate unique id if it isn't present in the request
            if 'walletId' not in request_json:
                request_json['walletId'] = str(uuid.uuid1())
            # update the database
            dynamodb.Table(WALLETS_TABLE).put_item(
                TableName= WALLETS_TABLE,
                Item=request_json
                )
            response_body = request_json
            status_code = 201

        # Update a specific operation by ID
        if route_key == 'PUT /users/{userId}/wallets/{walletId}/operations/{operationId}':
            # update item in the database
            request_json = json.loads(event['body'])

            # check if it has a valid body
            if not is_valid_body(request_json):
                return response(400, {'message': 'Error: Invalid body fields'})

            request_json['walletId'] = event['pathParameters']['walletId']
            # update the database
            dynamodb.Table(WALLETS_TABLE).put_item(TableName= WALLETS_TABLE,Item=request_json)
            response_body = request_json
            status_code = 200
    except Exception as err:
        status_code = 400
        response_body = {'Error:': str(err)}
        print(str(err))
    return response(status_code, response_body, headers)


def get_user_by_id(userId):
    # get data from the database
    ddb_response = dynamodb.Table(USERS_TABLE).get_item(Key={'userId': userId})
    # return single item instead of full DynamoDB response
    if 'Item' in ddb_response:
        return ddb_response['Item']
    else:
        return


def get_wallet_by_id(walletId):
    # get data from the database
    ddb_response = dynamodb.Table(WALLETS_TABLE).get_item(
        TableName= WALLETS_TABLE,
        Key={'walletId': walletId})
    # return single item instead of full DynamoDB response
    if 'Item' in ddb_response:
        return ddb_response['Item']
    else:
        return


def get_asset_by_id(assetId):
    # get data from the database
    ddb_response = dynamodb.Table(ASSETS_TABLE).get_item(Key={'assetId': assetId})
    # return single item instead of full DynamoDB response
    if 'Item' in ddb_response:
        return ddb_response['Item']
    else:
        return


def response(status_code, body, additional_headers=None):
    headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    # if additional_headers:
    #     headers.update(additional_headers)

    return {'statusCode': status_code, 'body': json.dumps(body), 'headers': headers}


def is_valid_body(request_json):
    try:
        return (
            request_json
            and 'amount' in request_json
            and 'type' in request_json
            and 'walletId' in request_json
        )
    except (json.JSONDecodeError, KeyError):
        return False
