# Write Super Dynamite proto files with exact known-correct bytes.
# Derived from vanilla protos 51 (inert) and 52 (active) with PID/TextID patched.
# All other fields identical to vanilla.

$protoDir = "C:\Games\F2Modding\Fallout 2\data\proto\items"

# Proto 534 — Super Dynamite (inert), based on vanilla 51
# Fields: PID=534(0x216), TextID=53400(0xD098), FrmID=23(0x17),
#         Light=0,0, Item::flags=0xa0000008, Item::flagsExt=0x0000a800 (Use=0x800), Script=-1,
#         ItemType=5(Misc), Material=1, Size=1, Weight=5, Cost=500(0x1F4)
#         Tail: 0700002E 30FFFFFF FF000000 00000000 00
$p534 = [byte[]](
    0x00,0x00,0x02,0x16,  # PID 534
    0x00,0x00,0xD0,0x98,  # TextID 53400
    0x00,0x00,0x00,0x17,  # FrmID 23
    0x00,0x00,0x00,0x00,  # LightDistance 0
    0x00,0x00,0x00,0x00,  # LightIntensity 0
    0xA0,0x00,0x00,0x08,  # Item::flags 0xa0000008
    0x00,0x00,0xA8,0x00,  # Item::flagsExt 0x0000a800 (Use=0x800 required)
    0x00,0x00,0x05,0x17,  # ScriptID 1303 (DYNMK2.int, 0-based index in scripts.lst)
    0x00,0x00,0x00,0x05,  # ItemType Misc
    0x00,0x00,0x00,0x01,  # Material
    0x00,0x00,0x00,0x01,  # Size
    0x00,0x00,0x00,0x05,  # Weight 5
    0x00,0x00,0x01,0xF4,  # Cost 500
    0x07,0x00,0x00,0x2E,  # Tail - misc type data
    0x30,0xFF,0xFF,0xFF,
    0xFF,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,
    0x00                   # 69 bytes total
)

# Proto 535 — Super Dynamite (active), based on vanilla 52
# Fields: PID=535(0x217), TextID=53500(0xD0FC), FrmID=23(0x17) [user's icon choice],
#         Light=0,0, Item::flags=0xa0000008, Item::flagsExt=0x0000a800 (Use=0x800), Script=-1,
#         ItemType=5(Misc), Material=1, Size=1, Weight=4, Cost=650(0x28A)
#         Tail: 0700002F 30000000 26000000 03000000 C8
$p535 = [byte[]](
    0x00,0x00,0x02,0x17,  # PID 535
    0x00,0x00,0xD0,0xFC,  # TextID 53500
    0x00,0x00,0x00,0x17,  # FrmID 23 (vanilla active uses 121; user controls this)
    0x00,0x00,0x00,0x00,  # LightDistance 0
    0x00,0x00,0x00,0x00,  # LightIntensity 0
    0xA0,0x00,0x00,0x08,  # Item::flags 0xa0000008
    0x00,0x00,0xA8,0x00,  # Item::flagsExt 0x0000a800 (Use=0x800 required)
    0x00,0x00,0x05,0x18,  # ScriptID 1304 (DYNMK2ON.int, 0-based index in scripts.lst)
    0x00,0x00,0x00,0x05,  # ItemType Misc
    0x00,0x00,0x00,0x01,  # Material
    0x00,0x00,0x00,0x01,  # Size
    0x00,0x00,0x00,0x04,  # Weight 4
    0x00,0x00,0x02,0x8A,  # Cost 650
    0x07,0x00,0x00,0x2F,  # Tail - misc type data (vanilla active)
    0x30,0x00,0x00,0x00,
    0x26,0x00,0x00,0x00,
    0x03,0x00,0x00,0x00,
    0xC8                   # 69 bytes total
)

$out534 = Join-Path $protoDir "00000534.pro"
$out535 = Join-Path $protoDir "00000535.pro"

# Clear read-only so we can overwrite
foreach ($f in @($out534, $out535)) {
    if (Test-Path $f) { Set-ItemProperty $f -Name IsReadOnly -Value $false }
}

[System.IO.File]::WriteAllBytes($out534, $p534)
[System.IO.File]::WriteAllBytes($out535, $p535)

# Mark read-only so the game's startup cleanup doesn't delete them
Set-ItemProperty $out534 -Name IsReadOnly -Value $true
Set-ItemProperty $out535 -Name IsReadOnly -Value $true

# Verify — cast to [int] before shifting to avoid byte overflow
function Read-Int32BE($bytes, $offset) {
    (([int]$bytes[$offset] -shl 24) -bor ([int]$bytes[$offset+1] -shl 16) -bor ([int]$bytes[$offset+2] -shl 8) -bor [int]$bytes[$offset+3])
}

foreach ($spec in @(
    @{ path=$out534; expPid=534; expScript=1303; expWgt=5  },
    @{ path=$out535; expPid=535; expScript=1304; expWgt=4  }
)) {
    $b    = [System.IO.File]::ReadAllBytes($spec.path)
    $ppid = Read-Int32BE $b 0
    $sid  = Read-Int32BE $b 28
    $wgt  = Read-Int32BE $b 44
    $extf = Read-Int32BE $b 24  # Item::flagsExt — must be 0x0000a800 (2726912) — has Use=0x800
    $ok   = if ($ppid -eq $spec.expPid -and $sid -eq $spec.expScript -and $wgt -eq $spec.expWgt -and $extf -eq 43008) { "OK" } else { "MISMATCH" }
    Write-Host "$([System.IO.Path]::GetFileName($spec.path)): PID=$ppid ScriptID=$sid Weight=$wgt ExtF=0x$('{0:X8}' -f $extf) [$ok]"
}
