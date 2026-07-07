# Run native Windows development server without a project-local venv.
# Execute from the src directory:
#   powershell -ExecutionPolicy Bypass -File .\runserver_native.ps1

$ErrorActionPreference = "Stop"

Write-Host "Installing Python dependencies globally/current Python..."
python -m pip install -r requirements\base.txt

Write-Host "Installing npm dependencies..."
npm install

Write-Host "Building Tailwind CSS..."
npm run build

Write-Host "Running Django migrations..."
python manage.py migrate

Write-Host "Starting Django development server..."
python manage.py runserver
