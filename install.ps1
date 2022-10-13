$venv_path = ".\.virtualenvs\autoscale_demo"
function Write-Log
{
    $level = $args[0].ToUpper()
    $message = $args[1..($args.Length)]
    $date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $output = "$date [$level] $message"

    if ($level -eq "ERROR")
    {
        Write-Host -ForegroundColor Red $output
    }
    elseif (($level -eq "WARNING") -Or ($level -eq "WARN"))
    {
        Write-Host -ForegroundColor Magenta $output
    }
    elseif ($level -eq "INFO")
    {
        Write-Host -ForegroundColor Green $output
    }
    else
    {
        Write-Host $output
    }
}
function Install-Python-Packages {
    Write-Log INFO "Installing Python virtualenv at $venv_path"
    python -m venv $venv_path
    . $venv_path\Scripts\Activate.ps1
    pip install -U pip 
    Get-ChildItem .\packages\ | 
      ForEach-Object{
         pip install $_.FullName
      }
      pip install retry
}
Install-Python-Packages