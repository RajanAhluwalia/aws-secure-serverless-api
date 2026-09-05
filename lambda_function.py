import json
import os
import boto3
from botocore.exceptions import ClientError

# Connect to DynamoDB
dynamodb = boto3.resource("dynamodb")

# Read table name from Lambda environment variable
table = dynamodb.Table(os.environ["TABLE_NAME"])


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }


def lambda_handler(event, context):

    try:
        # Get HTTP method from API Gateway
        method = event["requestContext"]["http"]["method"]

        # Get employeeId from URL path if present
        path_parameters = event.get("pathParameters") or {}
        employee_id = path_parameters.get("employeeId")

        # -------------------------
        # CREATE EMPLOYEE
        # -------------------------
        if method == "POST":

            body = json.loads(event.get("body") or "{}")

            # Validate required fields
            if not all(
                key in body
                for key in ["employeeID", "name", "department"]
            ):
                return response(
                    400,
                    {
                        "message":
                        "employeeID, name and department are required"
                    }
                )

            employee = {
                "employeeID": body["employeeID"],
                "name": body["name"],
                "department": body["department"]
            }

            try:
                table.put_item(
                    Item=employee,
                    ConditionExpression="attribute_not_exists(employeeID)"
                )

            except ClientError as error:

                if (
                    error.response["Error"]["Code"]
                    == "ConditionalCheckFailedException"
                ):
                    return response(
                        409,
                        {"message": "Employee already exists"}
                    )

                raise

            return response(
                201,
                {
                    "message": "Employee created successfully",
                    "employee": employee
                }
            )

        # -------------------------
        # GET EMPLOYEE
        # -------------------------
        elif method == "GET":

            if not employee_id:
                return response(
                    400,
                    {"message": "employeeId is required"}
                )

            result = table.get_item(
                Key={
                    "employeeID": employee_id
                }
            )

            employee = result.get("Item")

            if not employee:
                return response(
                    404,
                    {"message": "Employee not found"}
                )

            return response(
                200,
                employee
            )

        # -------------------------
        # UPDATE EMPLOYEE
        # -------------------------
        elif method == "PUT":

            if not employee_id:
                return response(
                    400,
                    {"message": "employeeId is required"}
                )

            body = json.loads(event.get("body") or "{}")

            if "name" not in body or "department" not in body:
                return response(
                    400,
                    {
                        "message":
                        "name and department are required"
                    }
                )

            result = table.update_item(
                Key={
                    "employeeID": employee_id
                },
                UpdateExpression=(
                    "SET #name = :name, "
                    "department = :department"
                ),
                ExpressionAttributeNames={
                    "#name": "name"
                },
                ExpressionAttributeValues={
                    ":name": body["name"],
                    ":department": body["department"]
                },
                ReturnValues="ALL_NEW"
            )

            return response(
                200,
                {
                    "message": "Employee updated successfully",
                    "employee": result["Attributes"]
                }
            )

        # -------------------------
        # DELETE EMPLOYEE
        # -------------------------
        elif method == "DELETE":

            if not employee_id:
                return response(
                    400,
                    {"message": "employeeId is required"}
                )

            table.delete_item(
                Key={
                    "employeeID": employee_id
                }
            )

            return response(
                200,
                {
                    "message": "Employee deleted successfully"
                }
            )

        # Unsupported HTTP method
        else:
            return response(
                405,
                {"message": "Method not allowed"}
            )

    except Exception as error:

        print(f"Error: {str(error)}")

        return response(
            500,
            {
                "message": "Internal server error",
                "error": str(error)
            }
        )
