"""
Centralized Configuration Validator for CryptoBoy Microservices
VoidCat RDC - Environment Variable Validation Framework

This module provides fail-fast validation for required environment variables,
preventing services from starting with incomplete or invalid configuration.

Security Enhancement: FLAW-005 Resolution
Phase 1: Critical Stabilization
"""

import os
import sys
from typing import Dict, List, Optional, Tuple

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


class ConfigurationError(Exception):
    """Raised when configuration validation fails"""

    pass


class EnvironmentValidator:
    """
    Validates environment variables for microservices.

    Provides centralized configuration checking to ensure all services
    start with required credentials and settings.
    """

    # Core infrastructure credentials (REQUIRED for all services)
    CORE_REQUIRED_VARS = {
        "RABBITMQ_USER": {
            "description": "RabbitMQ username",
            "default": None,  # No default = required
            "validation": lambda v: len(v) > 0,
        },
        "RABBITMQ_PASS": {
            "description": "RabbitMQ password",
            "default": None,  # No default = required
            "validation": lambda v: len(v) >= 8,  # Minimum password length
            "error_msg": "Password must be at least 8 characters",
        },
        "RABBITMQ_HOST": {
            "description": "RabbitMQ hostname",
            "default": "rabbitmq",
            "validation": lambda v: len(v) > 0,
        },
        "RABBITMQ_PORT": {
            "description": "RabbitMQ port",
            "default": "5672",
            "validation": lambda v: v.isdigit() and 1 <= int(v) <= 65535,
            "error_msg": "Port must be a valid number (1-65535)",
        },
    }

    # Redis configuration (REQUIRED for signal-cacher, trading-bot)
    REDIS_VARS = {
        "REDIS_HOST": {
            "description": "Redis hostname",
            "default": "redis",
            "validation": lambda v: len(v) > 0,
        },
        "REDIS_PORT": {
            "description": "Redis port",
            "default": "6379",
            "validation": lambda v: v.isdigit() and 1 <= int(v) <= 65535,
            "error_msg": "Port must be a valid number (1-65535)",
        },
    }

    # LLM service configuration (OPTIONAL - has fallbacks)
    LLM_VARS = {
        "OLLAMA_HOST": {
            "description": "Ollama LLM service host",
            "default": "http://localhost:11434",
            "validation": lambda v: v.startswith("http"),
            "error_msg": "Must be valid HTTP/HTTPS URL",
        },
        "OLLAMA_MODEL": {
            "description": "Ollama model name",
            "default": "mistral:7b",
            "validation": lambda v: len(v) > 0,
        },
        "HUGGINGFACE_MODEL": {
            "description": "HuggingFace sentiment model",
            "default": "ProsusAI/finbert",
            "validation": lambda v: "/" in v,  # Must be in format "org/model"
            "error_msg": "Must be in format 'organization/model'",
        },
    }

    # Exchange API credentials (REQUIRED for live trading)
    EXCHANGE_VARS = {
        "BINANCE_API_KEY": {
            "description": "Binance API key",
            "default": None,  # Required for live trading
            "validation": lambda v: len(v) > 20,  # API keys are long
            "error_msg": "API key appears invalid (too short)",
            "optional_if": "DRY_RUN=true",  # Not required in dry-run mode
        },
        "BINANCE_API_SECRET": {
            "description": "Binance API secret",
            "default": None,
            "validation": lambda v: len(v) > 20,
            "error_msg": "API secret appears invalid (too short)",
            "optional_if": "DRY_RUN=true",
        },
    }

    @staticmethod
    def validate_required_variables(
        required_vars: Dict[str, dict],
        service_name: str = "service",
        strict: bool = True,
    ) -> Tuple[bool, List[str]]:
        """
        Validate a set of required environment variables.

        Args:
            required_vars: Dictionary of variable specifications
            service_name: Name of service for logging
            strict: If True, raise exception on failure; if False, return status

        Returns:
            Tuple of (success: bool, errors: List[str])

        Raises:
            ConfigurationError: If validation fails and strict=True
        """
        errors = []
        warnings = []

        print(f"\n{GREEN}Validating configuration for: {service_name}{RESET}")
        print("=" * 60)

        for var_name, spec in required_vars.items():
            value = os.getenv(var_name)
            default = spec.get("default")
            description = spec.get("description", "")
            validation_func = spec.get("validation")
            error_msg = spec.get("error_msg", "Validation failed")
            optional_if = spec.get("optional_if")

            # Check if variable is optional based on condition
            if optional_if and EnvironmentValidator._check_condition(optional_if):
                if not value:
                    print(f"  {YELLOW}⊘ {var_name:25} (optional: {optional_if}){RESET}")
                    continue

            # Use default if not set
            if not value and default is not None:
                value = default
                print(f"  ✓ {var_name:25} = {value:30} (default)")
                continue

            # Required variable missing
            if not value and default is None:
                errors.append(f"{var_name}: REQUIRED but not set - {description}")
                print(f"  {RED}✗ {var_name:25} MISSING (required){RESET}")
                continue

            # Validate value
            if validation_func:
                try:
                    if not validation_func(value):
                        errors.append(f"{var_name}: {error_msg} (value: {value[:20]}...)")
                        print(f"  {RED}✗ {var_name:25} INVALID: {error_msg}{RESET}")
                        continue
                except Exception as e:
                    errors.append(f"{var_name}: Validation error - {e}")
                    print(f"  {RED}✗ {var_name:25} ERROR: {e}{RESET}")
                    continue

            # Success
            display_value = value[:30] if len(value) > 30 else value
            # Hide sensitive values
            if any(
                sensitive in var_name.upper()
                for sensitive in ["PASS", "SECRET", "KEY", "TOKEN"]
            ):
                display_value = "*" * 8

            print(f"  {GREEN}✓ {var_name:25} = {display_value:30}{RESET}")

        print("=" * 60)

        # Print summary
        if errors:
            print(f"\n{RED}✗ Configuration validation FAILED{RESET}")
            print(f"{RED}  Errors: {len(errors)}{RESET}")
            for error in errors:
                print(f"{RED}    - {error}{RESET}")

            if strict:
                raise ConfigurationError(f"Configuration validation failed: {len(errors)} errors")

            return False, errors

        else:
            print(f"\n{GREEN}✓ Configuration validation PASSED{RESET}")
            return True, []

    @staticmethod
    def _check_condition(condition: str) -> bool:
        """
        Check if a condition is met (e.g., 'DRY_RUN=true')

        Args:
            condition: Condition string in format 'VAR=value'

        Returns:
            True if condition is met
        """
        if "=" not in condition:
            return False

        var, expected_value = condition.split("=", 1)
        actual_value = os.getenv(var.strip())

        return actual_value is not None and actual_value.lower() == expected_value.lower()

    @staticmethod
    def validate_all_services(service_type: str = "all") -> None:
        """
        Validate environment variables for specific service types.

        Args:
            service_type: Type of service ('all', 'rabbitmq', 'redis', 'trading', etc.)

        Raises:
            ConfigurationError: If validation fails
        """
        required_vars = {}

        if service_type in ["all", "rabbitmq", "core"]:
            required_vars.update(EnvironmentValidator.CORE_REQUIRED_VARS)

        if service_type in ["all", "redis", "cacher", "trading"]:
            required_vars.update(EnvironmentValidator.REDIS_VARS)

        if service_type in ["all", "sentiment", "llm"]:
            required_vars.update(EnvironmentValidator.LLM_VARS)

        if service_type in ["trading", "live"]:
            required_vars.update(EnvironmentValidator.EXCHANGE_VARS)

        EnvironmentValidator.validate_required_variables(
            required_vars, service_name=service_type, strict=True
        )


def validate_env_for_service(service_name: str) -> None:
    """
    Convenience function to validate environment for a specific service.

    Usage in service __main__:
        from services.common.config_validator import validate_env_for_service

        if __name__ == "__main__":
            validate_env_for_service("sentiment-processor")
            main()

    Args:
        service_name: Name of the service

    Raises:
        SystemExit: If validation fails (exit code 1)
    """
    service_type_map = {
        "news-poller": "rabbitmq",
        "market-streamer": "rabbitmq",
        "sentiment-processor": "sentiment",
        "signal-cacher": "cacher",
        "trading-bot": "trading",
    }

    service_type = service_type_map.get(service_name, "core")

    try:
        EnvironmentValidator.validate_all_services(service_type)
    except ConfigurationError as e:
        print(f"\n{RED}FATAL: {e}{RESET}")
        print(f"{RED}Service '{service_name}' cannot start with invalid configuration{RESET}")
        print(f"\n{YELLOW}Please check your .env file and ensure all required variables are set.{RESET}")
        sys.exit(1)


# Command-line interface for manual validation
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate CryptoBoy environment configuration")
    parser.add_argument(
        "--service",
        choices=["all", "rabbitmq", "redis", "sentiment", "cacher", "trading"],
        default="all",
        help="Service type to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Exit with error code if validation fails",
    )

    args = parser.parse_args()

    try:
        EnvironmentValidator.validate_all_services(args.service)
        print(f"\n{GREEN}✓ All checks passed!{RESET}")
        sys.exit(0)
    except ConfigurationError as e:
        print(f"\n{RED}✗ Validation failed: {e}{RESET}")
        sys.exit(1) if args.strict else sys.exit(0)
