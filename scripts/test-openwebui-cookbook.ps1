[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://192.168.0.221:8080'
)

$ErrorActionPreference = 'Stop'
$password = (& wsl.exe sh -lc 'cat ~/.config/ailab/openwebui-admin-password').Trim()
if ($LASTEXITCODE -ne 0 -or $password.Length -lt 12) {
    throw 'The Open WebUI administrator password is unavailable.'
}

$signin = Invoke-RestMethod `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/auths/signin" `
    -ContentType 'application/json' `
    -Body (@{ email = 'isaac@ailab.local'; password = $password } | ConvertTo-Json) `
    -TimeoutSec 20
$headers = @{ Authorization = "Bearer $($signin.token)" }

$expectedModels = @(
    'isaac-general',
    'lab-operator',
    'project-copilot',
    'evidence-researcher',
    'dad-finance-guide'
)
foreach ($modelId in $expectedModels) {
    $model = Invoke-RestMethod `
        -Method Get `
        -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/models/model?id=$modelId" `
        -Headers $headers `
        -TimeoutSec 20
    if (-not $model.is_active) {
        throw "Cookbook model is not active: $modelId"
    }
}

$skills = Invoke-RestMethod -Headers $headers -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/skills/"
$prompts = Invoke-RestMethod -Headers $headers -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/prompts/"
$tools = Invoke-RestMethod -Headers $headers -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/tools/"
$knowledge = Invoke-RestMethod -Headers $headers -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/knowledge/"

$managedSkills = @($skills | Where-Object { $_.id -in @('analyze-company-fundamentals', 'compare-financial-scenarios', 'diagnose-lab-health', 'explain-personal-finance', 'improve-ai-cookbook', 'interpret-market-data', 'navigate-projects', 'research-finance-with-evidence', 'research-with-evidence', 'review-infrastructure-change') })
$managedPrompts = @($prompts | Where-Object { $_.command -in @('/company-fundamentals', '/cookbook-feedback', '/evidence-research', '/finance-research', '/finance-scenario', '/lab-status', '/project-orientation', '/review-infrastructure') })
$managedTools = @($tools | Where-Object { $_.id -in @('finance_calculator', 'finance_planner', 'finance_search', 'finance_visualizer', 'github_reader', 'lab_observer', 'market_data', 'official_finance_data', 'research_gateway') })
$managedKnowledge = @($knowledge.items | Where-Object { $_.name -in @('AI Lab Operating Manual', 'Projects Index', 'Family Finance Foundations') })

if ($managedSkills.Count -ne 10 -or $managedPrompts.Count -ne 8 -or $managedTools.Count -ne 9 -or $managedKnowledge.Count -ne 3) {
    throw "Cookbook inventory mismatch: $($managedSkills.Count) skills, $($managedPrompts.Count) prompts, $($managedTools.Count) tools, $($managedKnowledge.Count) knowledge collections."
}

$webSearch = Invoke-RestMethod `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/retrieval/process/web/search" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body (@{ queries = @('Bank of Canada overnight rate official') } | ConvertTo-Json) `
    -TimeoutSec 180
if (-not $webSearch.status -or $webSearch.loaded_count -lt 3 -or @($webSearch.filenames).Count -lt 3) {
    throw 'Open WebUI Web Search did not load the required multi-source result set.'
}

$body = @{
    model = 'dad-finance-guide'
    stream = $false
    tool_ids = @('finance_calculator')
    messages = @(
        @{
            role = 'user'
            content = 'You must use loan_payment. Calculate the monthly payment on a 300000 loan at 5 percent annual interest over 25 years.'
        }
    )
} | ConvertTo-Json -Depth 12
$response = Invoke-RestMethod `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/chat/completions" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $body `
    -TimeoutSec 240
$toolCall = @($response.choices[0].message.tool_calls)[0]
if ($response.choices[0].finish_reason -ne 'tool_calls' -or $toolCall.function.name -ne 'loan_payment') {
    throw 'Dad Finance Guide did not select the deterministic loan-payment tool.'
}
$arguments = $toolCall.function.arguments | ConvertFrom-Json
if ($arguments.principal -ne 300000 -or $arguments.annual_interest_percent -ne 5 -or $arguments.amortization_years -ne 25 -or $arguments.payments_per_year -ne 12) {
    throw 'Dad Finance Guide generated incorrect loan-payment arguments.'
}

$visualBody = @{
    model = 'dad-finance-guide'
    stream = $false
    tool_ids = @('finance_visualizer')
    messages = @(
        @{
            role = 'user'
            content = 'You must call render_finance_chart to make a pie chart titled Monthly Budget with labels Housing, Food, Savings and values 1800, 700, 500 in Canadian dollars.'
        }
    )
} | ConvertTo-Json -Depth 12
$visualResponse = Invoke-RestMethod `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/chat/completions" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $visualBody `
    -TimeoutSec 240
$visualToolCall = @($visualResponse.choices[0].message.tool_calls)[0]
$visualArguments = $visualToolCall.function.arguments | ConvertFrom-Json
if ($visualResponse.choices[0].finish_reason -ne 'tool_calls' -or $visualToolCall.function.name -ne 'render_finance_chart' -or $visualArguments.chart_type -ne 'pie' -or @($visualArguments.values).Count -ne 3) {
    throw 'Dad Finance Guide did not select the safe finance visualizer correctly.'
}

$labBody = @{
    model = 'lab-operator'
    stream = $false
    tool_ids = @('lab_observer')
    messages = @(@{ role = 'user'; content = 'You must call list_collections now. Do not answer from memory.' })
} | ConvertTo-Json -Depth 12
$labResponse = Invoke-RestMethod `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/chat/completions" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $labBody `
    -TimeoutSec 240
$labToolCall = @($labResponse.choices[0].message.tool_calls)[0]
if ($labResponse.choices[0].finish_reason -ne 'tool_calls' -or $labToolCall.function.name -ne 'list_collections') {
    throw 'Lab Operator did not select the read-only collection-list tool.'
}

$githubBody = @{
    model = 'project-copilot'
    stream = $false
    tool_ids = @('github_reader')
    messages = @(@{ role = 'user'; content = 'You must call repository_overview for owner isaacwallace123 and repository homelab-k8s. Do not answer from memory.' })
} | ConvertTo-Json -Depth 12
$githubResponse = Invoke-RestMethod `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/chat/completions" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $githubBody `
    -TimeoutSec 240
$githubToolCall = @($githubResponse.choices[0].message.tool_calls)[0]
$githubArguments = $githubToolCall.function.arguments | ConvertFrom-Json
if ($githubResponse.choices[0].finish_reason -ne 'tool_calls' -or $githubToolCall.function.name -ne 'repository_overview' -or $githubArguments.owner -ne 'isaacwallace123' -or $githubArguments.repository -ne 'homelab-k8s') {
    throw 'Project Copilot did not select the allowlisted GitHub overview tool correctly.'
}

$password = $null
$signin = $null
[pscustomobject]@{
    Models = $expectedModels.Count
    Skills = $managedSkills.Count
    Prompts = $managedPrompts.Count
    Tools = $managedTools.Count
    Knowledge = $managedKnowledge.Count
    FinanceToolSelection = 'passed'
    FinanceVisualization = 'passed'
    WebSearch = "passed ($($webSearch.loaded_count) loaded sources)"
    LabToolSelection = 'passed'
    GitHubToolSelection = 'passed'
}
