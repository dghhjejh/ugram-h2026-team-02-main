from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root_endpoint(client: TestClient) -> None:
    """Test the root endpoint returns correct status."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_docs_endpoints_are_available(client: TestClient) -> None:
    """Swagger UI and ReDoc should remain available for dynamic API documentation."""
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_openapi_documents_upload_flow_examples_and_errors(client: TestClient) -> None:
    """The upload flow should be documented with descriptions, examples, and error responses."""
    schema = client.get("/openapi.json").json()

    tags_by_name = {tag["name"]: tag for tag in schema["tags"]}
    assert "POST /images/presign" in tags_by_name["images"]["description"]

    presign_operation = schema["paths"]["/images/presign"]["post"]
    assert "Start the upload flow" in presign_operation["description"]
    assert presign_operation["responses"]["413"]["content"]["application/json"]["example"]["detail"].startswith(
        "Upload exceeds the maximum allowed size"
    )

    create_image_operation = schema["paths"]["/images"]["post"]
    assert "Finalize the upload workflow" in create_image_operation["description"]
    assert create_image_operation["responses"]["403"]["content"]["application/json"]["example"] == {
        "detail": "You can only create images for yourself"
    }

    schemas = schema["components"]["schemas"]
    assert schemas["ImagePresignResponse"]["example"]["expires_in"] == 900
    assert (
        schemas["ImageCreateRequest"]["example"]["mention_tags"][0]["user_id"] == "223e4567-e89b-12d3-a456-426614174000"
    )
    assert "view_url" in schemas["ImageResponse"]["example"]


def test_social_comment_endpoint_is_documented_and_returns_501(client: TestClient) -> None:
    """The placeholder comment endpoint should be explicit in both runtime behavior and OpenAPI."""
    schema = client.get("/openapi.json").json()

    social_tag = next(tag for tag in schema["tags"] if tag["name"] == "social")
    assert "501 Not Implemented" in social_tag["description"]

    comment_operation = schema["paths"]["/social/comment"]["post"]
    assert comment_operation["summary"] == "Comment on an image (not yet implemented)"
    assert comment_operation["responses"]["501"]["content"]["application/json"]["example"] == {
        "detail": "Comment posting is not implemented yet"
    }

    response = client.post("/social/comment")
    assert response.status_code == 501
    assert response.json() == {"detail": "Comment posting is not implemented yet"}
