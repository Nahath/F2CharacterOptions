# Recreate Super Dynamite proto files 534 and 535 from vanilla protos in master.dat

$master   = "C:\Games\F2Modding\Fallout 2\master.dat"
$protoDir = "C:\Games\F2Modding\Fallout 2\data\proto\items"

$mdata = [System.IO.File]::ReadAllBytes($master)
$mlen  = $mdata.Length

function Read-LE32($arr, $off) {
    [int]$arr[$off] -bor ([int]$arr[$off+1] -shl 8) -bor ([int]$arr[$off+2] -shl 16) -bor ([int]$arr[$off+3] -shl 24)
}
function Write-BE32($arr, $off, $val) {
    $arr[$off]   = ($val -shr 24) -band 0xFF
    $arr[$off+1] = ($val -shr 16) -band 0xFF
    $arr[$off+2] = ($val -shr  8) -band 0xFF
    $arr[$off+3] =  $val          -band 0xFF
}

# Parse DAT2 directory
$treeSize  = Read-LE32 $mdata ($mlen - 8)
$pos       = $mlen - 8 - $treeSize
$numFiles  = Read-LE32 $mdata $pos; $pos += 4

$files = @{}
for ($i = 0; $i -lt $numFiles; $i++) {
    $nl   = Read-LE32 $mdata $pos; $pos += 4
    $name = [System.Text.Encoding]::ASCII.GetString($mdata, $pos, $nl).ToLower(); $pos += $nl
    $comp = $mdata[$pos]; $pos++
    $real = Read-LE32 $mdata $pos; $pos += 4
    $pkd  = Read-LE32 $mdata $pos; $pos += 4
    $off  = Read-LE32 $mdata $pos; $pos += 4
    $files[$name] = @{comp=$comp; real=$real; pkd=$pkd; off=$off}
}

function Get-VanillaProto($protoId) {
    $key = "proto\items\{0:D8}.pro" -f $protoId
    if (-not $files.ContainsKey($key)) { throw "Proto $protoId not found in master.dat" }
    $f   = $files[$key]
    $raw = $mdata[$f.off..($f.off + $f.pkd - 1)]
    if ($f.comp -ne 0) {
        $ms = New-Object System.IO.MemoryStream(,$raw[2..($raw.Length-1)])
        $ds = New-Object System.IO.Compression.DeflateStream($ms, [System.IO.Compression.CompressionMode]::Decompress)
        $out = New-Object byte[] $f.real
        $ds.Read($out, 0, $f.real) | Out-Null
        $raw = $out
    }
    return [byte[]]$raw
}

# Proto 534: vanilla 51 with PID=534, TextID=53400, FrmID=23 (unchanged)
$p534 = Get-VanillaProto 51
Write-BE32 $p534  0 534    # PID
Write-BE32 $p534  4 53400  # TextID
$out534 = Join-Path $protoDir "00000534.pro"
[System.IO.File]::WriteAllBytes($out534, $p534)
Set-ItemProperty $out534 -Name IsReadOnly -Value $true
Write-Host "Written $out534 ($($p534.Length) bytes)"

# Proto 535: vanilla 52 with PID=535, TextID=53500, FrmID=23 (user's icon choice)
$p535 = Get-VanillaProto 52
Write-BE32 $p535  0 535    # PID
Write-BE32 $p535  4 53500  # TextID
Write-BE32 $p535  8 23     # FrmID: match inert icon
$out535 = Join-Path $protoDir "00000535.pro"
[System.IO.File]::WriteAllBytes($out535, $p535)
Set-ItemProperty $out535 -Name IsReadOnly -Value $true
Write-Host "Written $out535 ($($p535.Length) bytes)"

# Verify
foreach ($f in @($out534, $out535)) {
    $b = [System.IO.File]::ReadAllBytes($f)
    $pid  = ($b[0] -shl 24) -bor ($b[1] -shl 16) -bor ($b[2] -shl  8) -bor $b[3]
    $tid  = ($b[4] -shl 24) -bor ($b[5] -shl 16) -bor ($b[6] -shl  8) -bor $b[7]
    $frm  = ($b[8] -shl 24) -bor ($b[9] -shl 16) -bor ($b[10] -shl 8) -bor $b[11]
    $wgt  = ($b[44]-shl 24) -bor ($b[45]-shl 16) -bor ($b[46]-shl  8) -bor $b[47]
    $cst  = ($b[48]-shl 24) -bor ($b[49]-shl 16) -bor ($b[50]-shl  8) -bor $b[51]
    Write-Host "  PID=$pid TextID=$tid FrmID=$frm Weight=$wgt Cost=$cst"
}
