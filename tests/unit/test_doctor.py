from infinite_interns.doctor import CheckResult, run_doctor


def test_doctor_reports_failed_dependency() -> None:
    report = run_doctor(checks=[lambda: CheckResult(name="git", ok=False, detail="missing")])
    assert report.ready is False
    assert report.results[0].name == "git"
    assert report.results[0].detail == "missing"
