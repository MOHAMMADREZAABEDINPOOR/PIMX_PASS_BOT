# PowerShell script to run tests
Write-Host "Installing test dependencies..." -ForegroundColor Cyan
pip install pytest pytest-asyncio pytest-mock

Write-Host "`nRunning all tests..." -ForegroundColor Green
python -m pytest tests/test_scanner.py -v

Write-Host "`nTest run complete!" -ForegroundColor Green
