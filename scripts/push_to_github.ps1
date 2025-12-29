Param(
  [string]$repoName = "PIMX_PASS_BOT",
  [ValidateSet('public','private')]
  [string]$visibility = "public"
)

Write-Host "Logging in with GitHub CLI (interactive). Follow the prompts."
gh auth login

Write-Host "Creating repo $repoName (visibility: $visibility) and pushing..."
gh repo create $repoName --$visibility --source=. --remote=origin --push

Write-Host "Done. If you used HTTPS and entered credentials, the remote origin is set and main branch pushed."