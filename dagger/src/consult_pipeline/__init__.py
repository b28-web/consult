"""Consult CI/CD Pipeline - Dagger Module.

Pre-deployment validation pipeline that verifies the entire stack
before deployment. Designed for LLM agent automation.

Usage:
    just pre-deploy           # Full validation
    just pre-deploy-build     # Build only
    just pre-deploy-quality   # Quality checks only
"""

from .main import ConsultPipeline as ConsultPipeline
