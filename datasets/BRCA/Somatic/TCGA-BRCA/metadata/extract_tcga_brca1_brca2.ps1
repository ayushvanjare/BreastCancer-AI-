$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$raw = Join-Path $base 'raw'
$outDir = Join-Path $base 'derived'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$outPath = Join-Path $outDir 'tcga_brca1_brca2_somatic_variants.tsv'
$writer = [IO.StreamWriter]::new($outPath, $false, [Text.UTF8Encoding]::new($false))
$writer.AutoFlush = $false
$counts = @{ BRCA1 = 0; BRCA2 = 0 }
$samples = @{ BRCA1 = [Collections.Generic.HashSet[string]]::new(); BRCA2 = [Collections.Generic.HashSet[string]]::new() }
$headerWritten = $false
try {
  foreach ($file in Get-ChildItem -LiteralPath $raw -Filter '*.maf.gz' -File) {
    $fs = [IO.File]::OpenRead($file.FullName)
    $gz = [IO.Compression.GZipStream]::new($fs, [IO.Compression.CompressionMode]::Decompress)
    $reader = [IO.StreamReader]::new($gz)
    try {
      $header = $null
      while ($null -ne ($line = $reader.ReadLine())) {
        if ($line.StartsWith('#')) { continue }
        $header = $line
        break
      }
      if (-not $header) { continue }
      $columns = $header.Split("`t")
      $geneIndex = [Array]::IndexOf($columns, 'Hugo_Symbol')
      $sampleIndex = [Array]::IndexOf($columns, 'Tumor_Sample_Barcode')
      if ($geneIndex -lt 0) { throw "Hugo_Symbol column missing in $($file.Name)" }
      if (-not $headerWritten) { $writer.WriteLine("GDC_Source_File`t$header"); $headerWritten = $true }
      while ($null -ne ($line = $reader.ReadLine())) {
        $values = $line.Split("`t")
        if ($values.Length -le $geneIndex) { continue }
        $gene = $values[$geneIndex]
        if ($gene -notin @('BRCA1','BRCA2')) { continue }
        $writer.WriteLine("$($file.Name)`t$line")
        $counts[$gene]++
        if ($sampleIndex -ge 0 -and $values.Length -gt $sampleIndex -and $values[$sampleIndex]) { [void]$samples[$gene].Add($values[$sampleIndex]) }
      }
    } finally { $reader.Dispose() }
  }
} finally { $writer.Dispose() }
[PSCustomObject]@{SourceFiles=(Get-ChildItem -LiteralPath $raw -Filter '*.maf.gz' -File).Count; Output=$outPath; BRCA1VariantRows=$counts.BRCA1; BRCA1TumorSampleBarcodes=$samples.BRCA1.Count; BRCA2VariantRows=$counts.BRCA2; BRCA2TumorSampleBarcodes=$samples.BRCA2.Count; OutputBytes=(Get-Item $outPath).Length} | Format-List
