# Sample allgreen.py configuration file
# This demonstrates various types of health checks

@check("Basic truth check")
def basic_check():
    make_sure(True, "This should always pass")


@check("Math works correctly")
def math_check():
    expect(2 + 2).to_eq(4)
    expect(10).to_be_greater_than(5)
    expect(3).to_be_less_than(8)


@check("Environment variables are accessible")
def env_check():
    import os
    make_sure('PATH' in os.environ, "PATH environment variable should exist")


@check("Production only check", only="production")
def production_check():
    make_sure(ENVIRONMENT == "production", "Should only run in production")


@check("Skip in development", except_env="development")
def skip_dev_check():
    make_sure(True, "This should be skipped in development")


@check("Conditional check", if_condition=lambda: True)
def conditional_check():
    make_sure(True, "Condition was met")


# Example of a check that would normally fail
@check("Example failing check")
def failing_check():
    expect(1 + 1).to_eq(2)  # This will fail


# Example database connection check (commented out since we don't have DB)
# @check("Database connection is active")
# def db_check():
#     import sqlite3
#     conn = sqlite3.connect(':memory:')
#     make_sure(conn is not None, "Should be able to create in-memory database")
#     conn.close()


# Example system resource check
@check("System has some available memory")
def memory_check():
    try:
        import psutil
        memory = psutil.virtual_memory()
        expect(memory.percent).to_be_less_than(95)
    except ImportError:
        # psutil not available, skip this check
        make_sure(True, "psutil not available, skipping memory check")
