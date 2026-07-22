[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://192.168.0.221:8080'
)

$ErrorActionPreference = 'Stop'
$socket = [System.Net.WebSockets.ClientWebSocket]::new()
try {
    $socket.Options.SetRequestHeader('Origin', $BaseUrl.TrimEnd('/'))
    $socketUrl = "$($BaseUrl.TrimEnd('/') -replace '^http', 'ws')/ws/socket.io/?EIO=4&transport=websocket"
    $null = $socket.ConnectAsync(
        [Uri]$socketUrl,
        [System.Threading.CancellationToken]::None
    ).GetAwaiter().GetResult()
    $socketBuffer = New-Object byte[] 2048
    $socketSegment = [ArraySegment[byte]]::new($socketBuffer)
    $socketResult = $socket.ReceiveAsync(
        $socketSegment,
        [System.Threading.CancellationToken]::None
    ).GetAwaiter().GetResult()
    $socketGreeting = [System.Text.Encoding]::UTF8.GetString(
        $socketBuffer,
        0,
        $socketResult.Count
    )
    if ($socketGreeting -notmatch '^0\{"sid"') {
        throw 'Open WebUI did not return a valid Socket.IO handshake.'
    }
}
finally {
    $socket.Dispose()
}

$password = (& wsl.exe sh -lc 'cat ~/.config/ailab/openwebui-admin-password').Trim()
if ($LASTEXITCODE -ne 0 -or $password.Length -lt 12) {
    throw 'The Open WebUI administrator password is unavailable.'
}

$signinBody = @{
    email = 'isaac@ailab.local'
    password = $password
} | ConvertTo-Json
$signin = Invoke-RestMethod `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/auths/signin" `
    -ContentType 'application/json' `
    -Body $signinBody `
    -TimeoutSec 20
$headers = @{ Authorization = "Bearer $($signin.token)" }

$models = Invoke-RestMethod `
    -Method Get `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/models" `
    -Headers $headers `
    -TimeoutSec 20
if ('ailab-grounded' -notin @($models.data.id)) {
    throw 'Open WebUI does not publish the ailab-grounded model.'
}
if ('ailab-assistant' -notin @($models.data.id)) {
    throw 'Open WebUI does not publish the ailab-assistant model.'
}

function Invoke-GroundedChat {
    param([array]$Messages)

    $body = @{
        model = 'ailab-grounded'
        stream = $false
        messages = $Messages
    } | ConvertTo-Json -Depth 12
    $response = Invoke-RestMethod `
        -Method Post `
        -Uri "$($BaseUrl.TrimEnd('/'))/api/chat/completions" `
        -Headers $headers `
        -ContentType 'application/json' `
        -Body $body `
        -TimeoutSec 240
    return $response.choices[0].message.content
}

$priorityQuestion = 'What are the three highest-priority unfinished items in the AI lab roadmap?'
$priorityAnswer = Invoke-GroundedChat -Messages @(
    @{ role = 'user'; content = $priorityQuestion }
)
$requiredPriorityTerms = @('platform boundary', 'grounded answers', 'tool plane')
foreach ($term in $requiredPriorityTerms) {
    if ($priorityAnswer -notmatch [regex]::Escape($term)) {
        throw "The roadmap answer omitted the required concept: $term"
    }
}
if ($priorityAnswer -notmatch 'ailab:docs/roadmap\.md lines 3-\d+') {
    throw 'The roadmap answer did not cite the authoritative priority queue.'
}

$followUpQuestion = 'Which one should I do first, and why?'
$followUpAnswer = Invoke-GroundedChat -Messages @(
    @{ role = 'user'; content = $priorityQuestion },
    @{ role = 'assistant'; content = $priorityAnswer },
    @{ role = 'user'; content = $followUpQuestion }
)
if ($followUpAnswer -notmatch 'platform boundary') {
    throw 'The follow-up answer lost the roadmap conversation context.'
}
if ($followUpAnswer -notmatch 'ailab:docs/roadmap\.md lines 3-\d+') {
    throw 'The follow-up answer was not grounded in the authoritative priority queue.'
}

$streamBody = @{
    model = 'ailab-grounded'
    stream = $true
    messages = @(
        @{ role = 'user'; content = 'What is the top AI lab roadmap priority?' }
    )
} | ConvertTo-Json -Depth 12
$stream = Invoke-WebRequest `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/chat/completions" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $streamBody `
    -TimeoutSec 240 `
    -UseBasicParsing
if ($stream.Headers['Content-Type'] -notmatch '^text/event-stream') {
    throw 'Open WebUI did not return the grounded answer as an SSE stream.'
}
if ($stream.Content -notmatch 'platform boundary' -or $stream.Content -notmatch '\[DONE\]') {
    throw 'The Open WebUI grounded SSE stream was incomplete or incorrect.'
}

$assistantStreamBody = @{
    model = 'ailab-assistant'
    stream = $true
    messages = @(
        @{ role = 'user'; content = 'In about 80 words, explain what makes a useful AI assistant.' }
    )
} | ConvertTo-Json -Depth 12
$assistantStream = Invoke-WebRequest `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/chat/completions" `
    -Headers $headers `
    -ContentType 'application/json' `
    -Body $assistantStreamBody `
    -TimeoutSec 240 `
    -UseBasicParsing
$assistantContentChunks = ([regex]::Matches($assistantStream.Content, '"content":')).Count
if ($assistantContentChunks -lt 10 -or $assistantStream.Content -notmatch '\[DONE\]') {
    throw 'Open WebUI did not forward multiple upstream ailab-assistant content chunks.'
}

[pscustomobject]@{
    RealtimeSocketPassed = $true
    ModelVisible = $true
    PriorityAnswerPassed = $true
    FollowUpContextPassed = $true
    StreamingPassed = $true
    TrueAssistantStreamingPassed = $true
    AssistantContentChunks = $assistantContentChunks
    Citation = 'ailab:docs/roadmap.md, Current Priority Queue'
} | ConvertTo-Json
