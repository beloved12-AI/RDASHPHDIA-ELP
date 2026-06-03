# RDASHPHDIA-ELP — Hybrid Particles Optimization Service

Opinionated scaffold for the Hybrid Particles Optimization microservice used in the RDASHPHDIA-ELP project.

Contents:
- FastAPI service (app/)
- Dockerfile
- requirements.txt
- Helm chart (charts/hybrid-opt)
- ArgoCD app manifest (infra/argocd)
- GitHub Actions workflows (CI + optional Helm CD)
- Makefile

Usage
- Build locally: make build
- Run locally: make run
- Run tests: make test
- Deploy with Helm: helm upgrade --install hybrid-opt charts/hybrid-opt
