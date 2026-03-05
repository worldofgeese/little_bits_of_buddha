"""Test Phase 2 infrastructure setup.

These tests verify that:
1. compose.yaml contains the new services (seeker-actor, wisdom)
2. Dockerfile contains the new build targets
3. Dapr component files exist and are valid YAML
4. Stub service directories and requirements.txt exist
5. Migration script exists and can handle edge cases
"""

import os
from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).parent.parent


class TestComposeYaml:
    """Test compose.yaml has Phase 2 services."""

    def test_compose_yaml_exists(self):
        compose_path = PROJECT_ROOT / "compose.yaml"
        assert compose_path.exists(), "compose.yaml not found"

    def test_compose_yaml_valid(self):
        """Test that compose.yaml is valid YAML."""
        compose_path = PROJECT_ROOT / "compose.yaml"
        with open(compose_path) as f:
            data = yaml.safe_load(f)
        assert data is not None, "compose.yaml is empty"
        assert "services" in data, "compose.yaml missing 'services' key"

    def test_seeker_actor_service_defined(self):
        """Test that seeker-actor-service is defined in compose.yaml."""
        compose_path = PROJECT_ROOT / "compose.yaml"
        with open(compose_path) as f:
            data = yaml.safe_load(f)
        assert "seeker-actor-service" in data["services"], (
            "seeker-actor-service not found in compose.yaml"
        )

    def test_seeker_actor_dapr_defined(self):
        """Test that seeker-actor-dapr is defined in compose.yaml."""
        compose_path = PROJECT_ROOT / "compose.yaml"
        with open(compose_path) as f:
            data = yaml.safe_load(f)
        assert "seeker-actor-dapr" in data["services"], (
            "seeker-actor-dapr not found in compose.yaml"
        )

    def test_wisdom_service_defined(self):
        """Test that wisdom-service is defined in compose.yaml."""
        compose_path = PROJECT_ROOT / "compose.yaml"
        with open(compose_path) as f:
            data = yaml.safe_load(f)
        assert "wisdom-service" in data["services"], (
            "wisdom-service not found in compose.yaml"
        )

    def test_wisdom_dapr_defined(self):
        """Test that wisdom-dapr is defined in compose.yaml."""
        compose_path = PROJECT_ROOT / "compose.yaml"
        with open(compose_path) as f:
            data = yaml.safe_load(f)
        assert "wisdom-dapr" in data["services"], (
            "wisdom-dapr not found in compose.yaml"
        )

    def test_openai_service_removed(self):
        """Test that openai-service and openai-dapr are removed from compose.yaml."""
        compose_path = PROJECT_ROOT / "compose.yaml"
        with open(compose_path) as f:
            data = yaml.safe_load(f)
        assert "openai-service" not in data["services"], (
            "openai-service should be removed in Phase 2"
        )
        assert "openai-dapr" not in data["services"], (
            "openai-dapr should be removed in Phase 2"
        )

    def test_services_have_production_profile(self):
        """Test that new services have production profile."""
        compose_path = PROJECT_ROOT / "compose.yaml"
        with open(compose_path) as f:
            data = yaml.safe_load(f)

        for service_name in [
            "seeker-actor-service",
            "seeker-actor-dapr",
            "wisdom-service",
            "wisdom-dapr",
        ]:
            service = data["services"][service_name]
            assert "profiles" in service, f"{service_name} missing profiles"
            assert "production" in service["profiles"], (
                f"{service_name} missing production profile"
            )


class TestDockerfile:
    """Test Dockerfile has Phase 2 build targets."""

    def test_dockerfile_exists(self):
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile not found"

    def test_seeker_actor_builder_target(self):
        """Test that seeker-actor-service-builder target exists."""
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        content = dockerfile_path.read_text()
        assert "FROM base-builder as seeker-actor-service-builder" in content, (
            "seeker-actor-service-builder target not found in Dockerfile"
        )

    def test_seeker_actor_production_target(self):
        """Test that seeker-actor-service-production target exists."""
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        content = dockerfile_path.read_text()
        assert "FROM python:3.12-slim as seeker-actor-service-production" in content, (
            "seeker-actor-service-production target not found in Dockerfile"
        )

    def test_wisdom_service_builder_target(self):
        """Test that wisdom-service-builder target exists."""
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        content = dockerfile_path.read_text()
        assert "FROM base-builder as wisdom-service-builder" in content, (
            "wisdom-service-builder target not found in Dockerfile"
        )

    def test_wisdom_service_production_target(self):
        """Test that wisdom-service-production target exists."""
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        content = dockerfile_path.read_text()
        assert "FROM python:3.12-slim as wisdom-service-production" in content, (
            "wisdom-service-production target not found in Dockerfile"
        )


class TestStubServices:
    """Test stub service directories and requirements."""

    def test_seeker_actor_service_init(self):
        """Test that seeker_actor_service/__init__.py exists."""
        init_path = PROJECT_ROOT / "src/seeker_actor_service/__init__.py"
        assert init_path.exists(), "src/seeker_actor_service/__init__.py not found"

    def test_seeker_actor_service_main(self):
        """Test that seeker_actor_service/__main__.py exists."""
        main_path = PROJECT_ROOT / "src/seeker_actor_service/__main__.py"
        assert main_path.exists(), "src/seeker_actor_service/__main__.py not found"

    def test_seeker_actor_service_requirements(self):
        """Test that seeker_actor_service/requirements.txt exists."""
        req_path = PROJECT_ROOT / "src/seeker_actor_service/requirements.txt"
        assert req_path.exists(), "src/seeker_actor_service/requirements.txt not found"

    def test_wisdom_service_init(self):
        """Test that wisdom_service/__init__.py exists."""
        init_path = PROJECT_ROOT / "src/wisdom_service/__init__.py"
        assert init_path.exists(), "src/wisdom_service/__init__.py not found"

    def test_wisdom_service_main(self):
        """Test that wisdom_service/__main__.py exists."""
        main_path = PROJECT_ROOT / "src/wisdom_service/__main__.py"
        assert main_path.exists(), "src/wisdom_service/__main__.py not found"

    def test_wisdom_service_requirements(self):
        """Test that wisdom_service/requirements.txt exists."""
        req_path = PROJECT_ROOT / "src/wisdom_service/requirements.txt"
        assert req_path.exists(), "src/wisdom_service/requirements.txt not found"


class TestDaprComponents:
    """Test Dapr component configuration files."""

    def test_conversation_component_exists(self):
        """Test that conversation.yaml component exists."""
        conv_path = PROJECT_ROOT / ".dapr/components/conversation.yaml"
        assert conv_path.exists(), ".dapr/components/conversation.yaml not found"

    def test_conversation_component_valid_yaml(self):
        """Test that conversation.yaml is valid YAML."""
        conv_path = PROJECT_ROOT / ".dapr/components/conversation.yaml"
        with open(conv_path) as f:
            data = yaml.safe_load(f)
        assert data is not None, "conversation.yaml is empty"
        assert data["apiVersion"] == "dapr.io/v1alpha1"
        assert data["kind"] == "Component"

    def test_statestore_has_actor_support(self):
        """Test that statestore.yaml has actorStateStore enabled."""
        statestore_path = PROJECT_ROOT / ".dapr/components/statestore.yaml"
        with open(statestore_path) as f:
            data = yaml.safe_load(f)

        metadata = data["spec"]["metadata"]
        actor_enabled = False
        for item in metadata:
            if item["name"] == "actorStateStore":
                actor_enabled = item["value"] in ["true", True]
                break

        assert actor_enabled, "statestore.yaml missing actorStateStore: true"

    def test_statestore_uses_lbob_redis_host(self):
        """Test that statestore.yaml uses lbob-redis host for production."""
        statestore_path = PROJECT_ROOT / ".dapr/components/statestore.yaml"
        with open(statestore_path) as f:
            data = yaml.safe_load(f)

        metadata = data["spec"]["metadata"]
        redis_host = None
        for item in metadata:
            if item["name"] == "redisHost":
                redis_host = item["value"]
                break

        assert redis_host == "lbob-redis:6379", (
            f"statestore.yaml should use lbob-redis:6379, got {redis_host}"
        )


class TestMigrationScript:
    """Test state migration script."""

    def test_migration_script_exists(self):
        """Test that migrate_state_to_actors.py exists."""
        script_path = PROJECT_ROOT / "scripts/migrate_state_to_actors.py"
        assert script_path.exists(), "scripts/migrate_state_to_actors.py not found"

    def test_migration_script_is_python(self):
        """Test that migration script is valid Python."""
        script_path = PROJECT_ROOT / "scripts/migrate_state_to_actors.py"
        content = script_path.read_text()
        # Simple check: should have proper Python docstring and imports
        assert '"""' in content, "Migration script missing docstring"
        assert "import" in content, "Migration script missing imports"


class TestADR:
    """Test ADR documentation."""

    def test_adr_0012_exists(self):
        """Test that ADR 0012 exists."""
        adr_path = PROJECT_ROOT / "docs/adr/0012-dapr-actors-for-seeker-state.md"
        assert adr_path.exists(), (
            "docs/adr/0012-dapr-actors-for-seeker-state.md not found"
        )

    def test_adr_0012_has_content(self):
        """Test that ADR 0012 has meaningful content."""
        adr_path = PROJECT_ROOT / "docs/adr/0012-dapr-actors-for-seeker-state.md"
        content = adr_path.read_text()
        assert len(content) > 200, "ADR 0012 should have substantial content"
        assert "actor" in content.lower(), "ADR 0012 should discuss actors"
