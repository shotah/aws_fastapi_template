from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from helper import Users, get_greeting_message, multiply_numbers  # type: ignore
from models import HelloResponse, UserCreateRequest, UserCreateResponse

app = APIGatewayRestResolver(enable_validation=True)
tracer = Tracer()
logger = Logger()
metrics = Metrics(namespace="Powertools")


@app.post("/users")
@tracer.capture_method
def create_user(user_request: UserCreateRequest) -> dict[str, Any]:
    """
    Create a new user with Pydantic validation and business logic.

    Flow:
    1. user_request is automatically validated by Pydantic (API contract)
    2. Users service handles business logic
    3. Returns domain User model
    4. Wrapped in UserCreateResponse (API contract)

    This demonstrates proper separation:
    - API models (UserCreateRequest/Response) in models.py
    - Domain model (User) in helper.py
    - Business logic (Users service) in helper.py
    - Orchestration here in app.py
    """
    metrics.add_metric(name="UserCreationAttempts", unit=MetricUnit.Count, value=1)

    logger.info("Creating new user", extra={"user_email": user_request.email})

    # Business logic in Users service - returns domain User model
    users_service = Users()
    user = users_service.create_user(
        name=user_request.name,
        email=user_request.email,
        age=user_request.age,
        is_active=user_request.is_active,
    )

    # Wrap domain model in API response
    response = UserCreateResponse(
        status="success",
        message=f"User {user_request.name} created successfully",
        user=user,  # Domain model from helper.py!
    )

    return response.model_dump()


@app.get("/hello")
@tracer.capture_method
def hello() -> dict[str, Any]:
    """
    Example endpoint using helper function that returns Pydantic model.

    Demonstrates the circular dependency solution:
    - get_greeting_message() returns HelperModuleTest
    - Uses TYPE_CHECKING and runtime import in helper.py
    - No circular dependency issues!
    """
    # adding custom metrics
    # See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/metrics/
    metrics.add_metric(name="HelloWorldInvocations", unit=MetricUnit.Count, value=1)

    # Helper function returns a Pydantic model directly - no circular import!
    greeting_model = get_greeting_message("Lambda")
    test_multiply = multiply_numbers(6, 7)

    # structured log
    # See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/logger/
    logger.info("Hello world API - HTTP 200", extra={"helper_greeting": greeting_model.greeting})

    response = HelloResponse(
        message="hello world",
        helper_module_test=greeting_model,  # Already a Pydantic model!
        multiplication_result=test_multiply,
    )

    # APIGatewayRestResolver automatically serializes Pydantic models
    return response.model_dump()


# Enrich logging with contextual information from Lambda
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
# Adding tracer
# See: https://awslabs.github.io/aws-lambda-powertools-python/latest/core/tracer/
@tracer.capture_lambda_handler
# ensures metrics are flushed upon request completion/failure and
# capturing ColdStart metric
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict[str, Any]:
    return app.resolve(event, context)
