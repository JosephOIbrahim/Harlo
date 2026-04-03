# update_claude_desktop.ps1 — Update Claude Desktop MCP config to Harlo v8.0
# Run: powershell -ExecutionPolicy Bypass -File scripts\update_claude_desktop.ps1

$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"

if (Test-Path $configPath) {
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
    # Backup existing config
    Copy-Item $configPath "$configPath.bak" -Force
    Write-Host "Backed up existing config to $configPath.bak"
} else {
    $config = [PSCustomObject]@{}
}

# Build the new mcpServers block
$mcpServers = @{
    "harlo" = @{
        command = "C:/Users/User/Harlo/.venv/Scripts/harlo.exe"
        env = @{
            ANTHROPIC_API_KEY = $env:ANTHROPIC_API_KEY
        }
    }
}

# Preserve existing preferences if present
$preferences = $null
if ($config.PSObject.Properties["preferences"]) {
    $preferences = $config.preferences
}

$newConfig = [ordered]@{
    mcpServers = $mcpServers
}
if ($preferences) {
    $newConfig["preferences"] = $preferences
}

$json = $newConfig | ConvertTo-Json -Depth 10
$json | Set-Content $configPath -Encoding UTF8

Write-Host "Updated $configPath"
Write-Host ""
Write-Host "harlo -> .venv/Scripts/harlo.exe (v8.0)"
Write-Host "API key read from env:ANTHROPIC_API_KEY"
Write-Host ""
Write-Host "Restart Claude Desktop to pick up the change."
