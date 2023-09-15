import json
import os
import boto3
import uuid
import pytest
from moto import mock_dynamodb
from contextlib import contextmanager
from unittest.mock import patch

USERS_MOCK_TABLE_NAME = "UsersTest"
UUID_MOCK_VALUE_JOHN = "f8216640-91a2-11eb-8ab9-57aa454facef"
UUID_MOCK_VALUE_JANE = "31a9f940-917b-11eb-9054-67837e2c40b0"
UUID_MOCK_VALUE_NEW_USER = "new-user-guid"

ASSETS_MOCK_TABLE_NAME = "AssetsTest"
UUID_MOCK_VALUE_BTC = "09d97f0a-23e9-4930-a93a-cba3c9b7e9e2"
UUID_MOCK_VALUE_ETH = "79add0c4-4a41-4b5b-84a8-ad513242b390"


def mock_uuid():
    return UUID_MOCK_VALUE_NEW_USER


@contextmanager
def my_test_environment():
    with mock_dynamodb():
        set_up_dynamodb()
        put_data_dynamodb()
        yield


def set_up_dynamodb():
    conn = boto3.client("dynamodb")
    conn.create_table(
        TableName=USERS_MOCK_TABLE_NAME,
        KeySchema=[
            {"AttributeName": "userId", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[{"AttributeName": "userId", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    conn.create_table(
        TableName=ASSETS_MOCK_TABLE_NAME,
        KeySchema=[
            {"AttributeName": "assetId", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[{"AttributeName": "assetId", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )


def put_data_dynamodb():
    conn = boto3.client("dynamodb")
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            "userId": {"S": UUID_MOCK_VALUE_JOHN},
            "idNumber": {"S": "00000000A"},
            "firstName": {"S": "John"},
            "lastName": {"S": "Doe"},
            "email": {"S": "johndoe@gmail.com"},
            "phone": {"S": "600000001"},
        },
    )
    conn.put_item(
        TableName=USERS_MOCK_TABLE_NAME,
        Item={
            "userId": {"S": UUID_MOCK_VALUE_JANE},
            "idNumber": {"S": "00000000B"},
            "firstName": {"S": "Jane"},
            "lastName": {"S": "Doe"},
            "email": {"S": "janedoe@gmail.com"},
            "phone": {"S": "600000002"},
        },
    )
    conn.put_item(
        TableName=ASSETS_MOCK_TABLE_NAME,
        Item={
            "assetId": {"S": UUID_MOCK_VALUE_BTC},
            "symbol": {"S": "BTC"},
            "blockchain": {"S": "Bitcoin"},
        },
    )
    conn.put_item(
        TableName=ASSETS_MOCK_TABLE_NAME,
        Item={
            "assetId": {"S": UUID_MOCK_VALUE_ETH},
            "symbol": {"S": "ETH"},
            "blockchain": {"S": "Ethereum"},
        },
    )


@patch.dict(
    os.environ,
    {"USERS_TABLE": USERS_MOCK_TABLE_NAME, "AWS_XRAY_CONTEXT_MISSING": "LOG_ERROR"},
)
def test_get_list_of_users():
    with my_test_environment():
        from src.api import users

        with open("./events/users/event-get-all-users.json", "r") as f:
            apigw_get_all_users_event = json.load(f)
        expected_response = [
            {
                "userId": UUID_MOCK_VALUE_JOHN,
                "idNumber": "00000000A",
                "firstName": "John",
                "lastName": "Doe",
                "email": "johndoe@gmail.com",
                "phone": "600000001",
            },
            {
                "userId": UUID_MOCK_VALUE_JANE,
                "idNumber": "00000000B",
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "janedoe@gmail.com",
                "phone": "600000002",
            },
        ]
        ret = users.lambda_handler(apigw_get_all_users_event, "")
        assert ret["statusCode"] == 200
        data = json.loads(ret["body"])
        assert data == expected_response


def test_get_single_user():
    with my_test_environment():
        from src.api import users

        with open("./events/users/event-get-user-by-id.json", "r") as f:
            apigw_event = json.load(f)
        expected_response = {
            "userId": UUID_MOCK_VALUE_JOHN,
            "idNumber": "00000000A",
            "firstName": "John",
            "lastName": "Doe",
            "email": "johndoe@gmail.com",
            "phone": "600000001",
        }
        ret = users.lambda_handler(apigw_event, "")
        data = json.loads(ret["body"])
        assert data == expected_response
        assert ret["statusCode"] == 200


def test_get_single_user_wrong_id():
    with my_test_environment():
        from src.api import users

        with open("./events/users/event-get-user-by-id.json", "r") as f:
            apigw_event = json.load(f)
            apigw_event["pathParameters"]["userId"] = "123456789"
            apigw_event["rawPath"] = "/users/123456789"
        ret = users.lambda_handler(apigw_event, "")
        assert json.loads(ret["body"]) == {}
        assert ret["statusCode"] == 200


@patch("uuid.uuid1", mock_uuid)
@pytest.mark.freeze_time("2001-01-01")
def test_add_user():
    with my_test_environment():
        from src.api import users

        with open("./events/users/event-post-user.json", "r") as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event["body"])
        ret = users.lambda_handler(apigw_event, "")
        data = json.loads(ret["body"])
        assert data["userId"] == UUID_MOCK_VALUE_NEW_USER
        assert data["idNumber"] == expected_response["idNumber"]
        assert data["firstName"] == expected_response["firstName"]
        assert data["lastName"] == expected_response["lastName"]
        assert data["email"] == expected_response["email"]
        assert data["phone"] == expected_response["phone"]
        assert ret["statusCode"] == 200


def test_delete_user():
    with my_test_environment():
        from src.api import users

        with open("./events/users/event-delete-user-by-id.json", "r") as f:
            apigw_event = json.load(f)
        ret = users.lambda_handler(apigw_event, "")
        assert json.loads(ret["body"]) == {}
        assert ret["statusCode"] == 200


# Add your unit testing code here


@patch.dict(
    os.environ,
    {"ASSETS_TABLE": ASSETS_MOCK_TABLE_NAME, "AWS_XRAY_CONTEXT_MISSING": "LOG_ERROR"},
)
def test_get_list_of_assets():
    with my_test_environment():
        from src.api import assets

        with open("./events/assets/event-get-all-assets.json", "r") as f:
            apigw_get_all_assets_event = json.load(f)
        expected_response = [
            {
                "assetId": UUID_MOCK_VALUE_BTC,
                "symbol": "BTC",
                "blockchain": "Bitcoin",
            },
            {
                "assetId": UUID_MOCK_VALUE_BTC,
                "symbol": "BTC",
                "blockchain": "Bitcoin",
            },
        ]
        ret = assets.lambda_handler(apigw_get_all_assets_event, "")
        assert ret["statusCode"] == 200
        data = json.loads(ret["body"])
        assert data == expected_response
