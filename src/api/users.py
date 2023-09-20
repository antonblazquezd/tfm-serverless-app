import json
import uuid
import os
import boto3
from datetime import datetime

# Prepare DynamoDB client
dynamodb = boto3.resource("dynamodb")
USERS_TABLE = os.getenv("USERS_TABLE", None)
ddbUserTable = dynamodb.Table(USERS_TABLE)


def lambda_handler(event, context):
    route_key = f"{event['httpMethod']} {event['resource']}"

    # Set default response, override with data from DynamoDB if any
    response_body = {"Message": "Unsupported route"}
    status_code = 400

    try:
        # Get a list of all Users
        if route_key == "GET /users":
            ddb_response = ddbUserTable.scan(Select="ALL_ATTRIBUTES")
            # return list of items instead of full DynamoDB response
            response_body = ddb_response["Items"]
            status_code = 200

        # CRUD operations for a single User

        # Read a user by ID
        if route_key == "GET /users/{userId}":
            # get data from the database
            ddb_response = ddbUserTable.get_item(
                Key={"userId": event["pathParameters"]["userId"]}
            )
            # return single item instead of full DynamoDB response
            if "Item" in ddb_response:
                response_body = ddb_response["Item"]
            else:
                response_body = {}
            status_code = 200

        # Delete a user by ID
        if route_key == "DELETE /users/{userId}":
            # delete item in the database
            ddbUserTable.delete_item(Key={"userId": event["pathParameters"]["userId"]})
            response_body = {}
            status_code = 200

        # Create a new user
        if route_key == "POST /users":
            request_json = json.loads(event["body"])

            # check if it has a valid body
            if not is_valid_body(request_json):
                return response(400, {"Error": "Invalid body fields"})

            # generate unique id
            request_json["userId"] = str(uuid.uuid1())

            # update the database
            ddbUserTable.put_item(Item=request_json)
            response_body = request_json
            status_code = 200

        # Update a specific user by ID
        if route_key == "PUT /users/{userId}":
            # update item in the database
            request_json = json.loads(event["body"])

            # check if it has a valid body
            if not is_valid_body(request_json):
                return response(400, {"Error": "Invalid body fields"})

            request_json["userId"] = event["pathParameters"]["userId"]
            # update the database
            ddbUserTable.put_item(Item=request_json)
            response_body = request_json
            status_code = 200
    except Exception as err:
        status_code = 400
        response_body = {"Error:": str(err)}
        print(str(err))
    return response(status_code, response_body)


def response(status_code, body):
    headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}

    return {"statusCode": status_code, "body": json.dumps(body), "headers": headers}


def is_valid_body(request_json):
    try:
        return (
            request_json
            and "idNumber" in request_json
            and "firstName" in request_json
            and "lastName" in request_json
            and "email" in request_json
            and "phone" in request_json
        )
    except (json.JSONDecodeError, KeyError):
        return False
