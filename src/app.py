from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import BaseModel, ConfigDict, Field

from helper import get_greeting_message, multiply_numbers  # type: ignore

app = APIGatewayRestResolver(enable_validation=True)
tracer = Tracer()
logger = Logger()
metrics = Metrics(namespace="Powertools")


# Pydantic model for POST request validation
class UserCreateRequest(BaseModel):
    """Request model for creating a user."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "age": 30,
                "is_active": True,
            }
        }
    )

    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: str = Field(..., description="User's email address")
    age: int = Field(..., ge=0, le=150, description="User's age")
    is_active: bool = Field(default=True, description="Whether the user is active")


@app.post("/users")
@tracer.capture_method
def create_user(user: UserCreateRequest):
    """
    Create a new user with validated data.

    The Pydantic model validation happens BEFORE this function is called.
    If validation fails, APIGatewayRestResolver returns 422 automatically.
    """
    # Log the validated user data
    logger.info("Creating user", extra={"user_data": user.model_dump()})

    # Add metric for user creation
    metrics.add_metric(name="UserCreations", unit=MetricUnit.Count, value=1)

    # Simulate user creation (in real app, you'd save to database)
    user_id = multiply_numbers(user.age, 1000)  # Using helper function

    return {
        "status": "success",
        "message": f"User {user.name} created successfully",
        "user": user.model_dump(),
        "generated_id": user_id,
    }


@app.get("/hello")
@tracer.capture_method
def hello():
    # adding custom metrics
    # See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/metrics/
    metrics.add_metric(name="HelloWorldInvocations", unit=MetricUnit.Count, value=1)

    # Test calling helper module functions
    greeting_data = get_greeting_message("Lambda")
    test_multiply = multiply_numbers(6, 7)

    # structured log
    # See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/logger/
    logger.info("Hello world API - HTTP 200", extra={"helper_test": greeting_data})

    return {
        "message": "hello world",
        "helper_module_test": greeting_data,
        "multiplication_result": test_multiply,
    }


# Enrich logging with contextual information from Lambda
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
# Adding tracer
# See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/tracer/
@tracer.capture_lambda_handler
# ensures metrics are flushed upon request completion/failure and
# capturing ColdStart metric
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
