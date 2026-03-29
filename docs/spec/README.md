# Test Specifications Index

This directory contains domain-specific test specifications for the Telegram Voice/Audio Bot project.

---

## Documents

| Document | Description | Coverage |
|----------|-------------|----------|
| [test-specifications.md](./test-specifications.md) | **Master specification** - Overview of all test domains, coverage summary, fixtures reference | All domains |
| [yandex-disk-client-spec.md](./yandex-disk-client-spec.md) | Yandex.Disk API client (`infrastructure/external_api/yandex_disk_client.py`) | 100% |
| [yadisk-api-routes-spec.md](./yadisk-api-routes-spec.md) | REST API routes (`interfaces/webapp/routes/yadisk_folders.py`) | 86% |

---

## Quick Reference

### Test Execution

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=infrastructure --cov=interfaces/webapp --cov-report=term-missing

# Specific domain
pytest tests/test_yandex_disk_client.py -v
pytest tests/test_yadisk_folders_routes.py -v
```

### Coverage Summary

| Domain | Statements | Covered | Coverage |
|--------|-----------|---------|----------|
| Yandex.Disk Client | 54 | 54 | 100% |
| REST API Routes | 58 | 50 | 86% |
| **Total** | **112** | **104** | **93%** |

### Test Count by Domain

| Domain | Tests | Percentage |
|--------|-------|------------|
| Yandex.Disk Client | 18 | 47% |
| REST API Routes | 20 | 53% |
| **Total** | **38** | **100%** |

---

## Related Documentation

- [Yandex.Disk Folder Tree API Plan](../plans/yadisk-folder-tree-api-plan.md) - Implementation plan
- [PROJECT.md](../PROJECT.md) - Project overview and configuration
- [API Documentation](https://<domain>/docs) - Swagger UI (when running)

---

## Directory Structure

```
docs/spec/
├── README.md                      # This file
├── test-specifications.md         # Master test specification
├── yandex-disk-client-spec.md     # Client library specification
└── yadisk-api-routes-spec.md      # REST API specification

tests/
├── conftest.py                    # Pytest fixtures
├── test_yandex_disk_client.py     # Client tests (18 tests)
└── test_yadisk_folders_routes.py  # Route tests (20 tests)
```

---

**Version:** 1.0  
**Last Updated:** 2026-03-29
