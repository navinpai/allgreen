import pytest

from allgreen import (
    CheckAssertionError,
    CheckStatus,
    check,
    expect,
    get_registry,
    make_sure,
)


def test_basic_check_passing():
    # Clear registry for clean test
    registry = get_registry()
    registry.clear()

    @check("Simple passing check")
    def simple_check():
        make_sure(True)

    checks = registry.get_checks()
    assert len(checks) == 1

    check_obj = checks[0]
    result = check_obj.execute()

    assert result.passed
    assert result.status == CheckStatus.PASSED
    assert "Check passed" in result.message


def test_basic_check_failing():
    registry = get_registry()
    registry.clear()

    @check("Simple failing check")
    def failing_check():
        make_sure(False, "This should fail")

    checks = registry.get_checks()
    check_obj = checks[0]
    result = check_obj.execute()

    assert result.failed
    assert result.status == CheckStatus.FAILED
    assert "This should fail" in result.message


def test_expectation_methods():
    # Test to_eq
    expect(5).to_eq(5)
    with pytest.raises(CheckAssertionError):
        expect(5).to_eq(10)

    # Test to_be_greater_than
    expect(10).to_be_greater_than(5)
    with pytest.raises(CheckAssertionError):
        expect(5).to_be_greater_than(10)

    # Test to_be_less_than
    expect(5).to_be_less_than(10)
    with pytest.raises(CheckAssertionError):
        expect(10).to_be_less_than(5)


def test_check_with_expectations():
    registry = get_registry()
    registry.clear()

    @check("Check with expectations")
    def expectation_check():
        expect(2 + 2).to_eq(4)
        expect(10).to_be_greater_than(5)
        expect(3).to_be_less_than(8)

    check_obj = registry.get_checks()[0]
    result = check_obj.execute()

    assert result.passed


def test_environment_conditions():
    registry = get_registry()
    registry.clear()

    @check("Production only check", only_in="production")
    def prod_check():
        make_sure(True)

    @check("Skip in development", except_in="development")
    def skip_dev_check():
        make_sure(True)

    checks = registry.get_checks()
    prod_result = checks[0].execute("development")
    skip_result = checks[1].execute("development")

    assert prod_result.skipped
    assert skip_result.skipped
    assert "Only runs in production" in prod_result.skip_reason
    assert "Skipped in development" in skip_result.skip_reason


def test_if_condition():
    registry = get_registry()
    registry.clear()

    @check("Conditional check", if_condition=lambda: 1 + 1 == 2)
    def conditional_check():
        make_sure(True)

    @check("False condition check", if_condition=False)
    def false_condition_check():
        make_sure(True)

    checks = registry.get_checks()
    true_result = checks[0].execute()
    false_result = checks[1].execute()

    assert true_result.passed
    assert false_result.skipped
    assert "Custom condition is False" in false_result.skip_reason
