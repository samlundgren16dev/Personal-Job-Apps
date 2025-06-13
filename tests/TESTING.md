# Testing and CI/CD Documentation

## Overview

This document describes the testing infrastructure and CI/CD pipeline setup for the Job Application Tracker project.

## Project Structure

```
Job-Application-Tracker/
├── tests/                      # Test directory (moved from root)
│   ├── __init__.py            # Makes tests a Python package
│   ├── test_constants.py      # Tests for constants module
│   ├── test_excel_handler.py  # Tests for Excel operations
│   ├── test_parsing.py        # Tests for job parsing functionality
│   └── run_tests.py           # Test runner script
├── dev/                       # Development files
│   └── working.py             # Legacy development code
├── .gitlab-ci.yml             # GitLab CI/CD pipeline configuration
├── pytest.ini                # Pytest configuration
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
└── [main application files]
```

## Testing Framework

### Unit Tests

The project uses Python's built-in `unittest` framework for testing with the following test modules:

1. **test_constants.py**: Tests application constants and configuration
   - Headers structure validation
   - Job status options validation
   - Color scheme consistency
   - Configuration structure validation

2. **test_excel_handler.py**: Tests Excel file operations
   - File finding and configuration management
   - Data import/export functionality
   - Statistics calculation
   - CSV import/export operations

3. **test_parsing.py**: Tests job parsing functionality
   - Job title validation and cleaning
   - Location validation and cleaning
   - Job type pattern recognition
   - URL parsing (with mocking)

### Running Tests

#### Using the custom test runner:
```bash
# Run all tests
python tests/run_tests.py

# Run specific test module
python tests/run_tests.py --module test_constants

# Run with different verbosity levels
python tests/run_tests.py --verbose
python tests/run_tests.py --quiet
```

#### Using pytest (if installed):
```bash
# Run all tests with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_constants.py -v

# Run tests with specific markers
pytest -m "not slow" tests/
```

### Test Configuration

The `pytest.ini` file contains:
- Test discovery patterns
- Coverage configuration
- Output formatting options
- Test markers for categorization

## CI/CD Pipeline

### GitLab CI/CD (.gitlab-ci.yml)

The pipeline consists of 5 stages:

#### 1. Lint Stage
- **pylint**: Code quality analysis with configurable fail thresholds
- **flake8**: Style and complexity checks
- **black**: Code formatting verification
- **isort**: Import statement ordering

#### 2. Test Stage
- **unit tests**: Comprehensive test suite execution
- **syntax checks**: Python syntax validation
- **metrics**: Code complexity analysis
- **license-check**: Dependency license compliance

#### 3. Security Stage
- **bandit**: Security vulnerability scanning
- **safety**: Known security vulnerability checks in dependencies

#### 4. Build Stage
- **package**: Creates distributable ZIP package
- **executable**: Builds standalone executable with PyInstaller
- **docs**: Generates Sphinx documentation (optional)

#### 5. Deploy Stage
- **dev**: Deploys to development environment (feature branches)
- **staging**: Manual deployment to staging (main branch)
- **production**: Manual deployment for tagged releases

### Pipeline Features

- **Caching**: Pip cache and virtual environment caching for faster builds
- **Artifacts**: Test reports, coverage reports, build artifacts
- **Environment-specific deployments**: Different deployment strategies per environment
- **Manual gates**: Production deployments require manual approval
- **Parallel execution**: Multiple jobs run simultaneously where possible

### Environment Variables

The pipeline uses these configurable variables:
- `PYTHON_VERSION`: Python version to use (default: 3.9)
- `PIP_CACHE_DIR`: Pip cache directory for faster installs

## Development Workflow

### Setting up Development Environment

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Install pre-commit hooks (if using):
   ```bash
   pre-commit install
   ```

3. Run tests locally before pushing:
   ```bash
   python tests/run_tests.py
   ```

### Code Quality Standards

The project enforces these quality standards:
- **PyLint score**: Minimum 8.0 for most modules, 7.0 for complex modules
- **Line length**: Maximum 100 characters
- **Test coverage**: Minimum 70% coverage target
- **Import organization**: Sorted with isort
- **Code formatting**: Black formatting standards

### Branch Strategy

- **feature/***: Feature development branches (auto-deploy to dev)
- **develop**: Development integration branch (auto-deploy to dev)
- **main**: Production-ready code (manual deploy to staging)
- **tags**: Release versions (manual deploy to production)

## Troubleshooting

### Common Test Issues

1. **Import errors**: Ensure you're running tests from the project root
2. **Missing dependencies**: Install test dependencies with `pip install pytest pytest-cov`
3. **Path issues**: Tests add parent directory to Python path automatically

### CI/CD Issues

1. **Linting failures**: Run `pylint [file]` locally to see specific issues
2. **Test failures**: Run tests locally with `python tests/run_tests.py --verbose`
3. **Build failures**: Check artifacts and logs in GitLab CI interface

### Performance Considerations

- Tests run in parallel where possible
- Browser-based tests are mocked to avoid slow execution
- Caching is used extensively to speed up pipeline execution
- Non-critical checks (like documentation) allow failures

## Contributing

When adding new features:

1. Write corresponding unit tests
2. Ensure all existing tests pass
3. Maintain or improve code coverage
4. Follow the established code style
5. Update documentation as needed

The CI/CD pipeline will automatically validate your changes when you push to GitLab.
