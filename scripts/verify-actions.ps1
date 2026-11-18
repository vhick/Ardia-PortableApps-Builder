$ErrorActionPreference='Stop'
$actions=@(
  @{Url='https://github.com/vhick/Portable-Package-Builder.git';Tag='v1.0.0';Prefix='0112c35'},
  @{Url='https://github.com/vhick/portable-release-publisher.git';Tag='v1.1.1';Prefix='cb64f86'}
)
foreach($a in $actions){
  $sha=''
  $line=@(& git ls-remote $a.Url ("refs/tags/"+$a.Tag+'^{}'))
  if($LASTEXITCODE -ne 0){throw "Could not verify signed/pinned action tag $($a.Url)@$($a.Tag)"}
  if($line.Count -gt 0){$sha=([string]$line[0] -split '\s+')[0]}
  else {
    $line=@(& git ls-remote $a.Url ("refs/tags/"+$a.Tag))
    if($LASTEXITCODE -ne 0 -or $line.Count -ne 1){throw "Action tag unresolved: $($a.Url)@$($a.Tag)"}
    $sha=([string]$line[0] -split '\s+')[0]
  }
  if($sha -notmatch '^[0-9a-f]{40}$' -or -not $sha.StartsWith($a.Prefix,[System.StringComparison]::OrdinalIgnoreCase)){
    throw "Pinned action tag changed from known release identity $($a.Prefix): $($a.Url) -> $sha"
  }
  Write-Host "VERIFIED ACTION TAG: $($a.Tag) -> $sha for $($a.Url)"
}
