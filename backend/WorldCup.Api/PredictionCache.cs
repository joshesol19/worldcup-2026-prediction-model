using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace WorldCup.Api;

public class PredictionCache
{
    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        NumberHandling = JsonNumberHandling.AllowReadingFromString,
    };

    public Cache2026? Data2026 { get; private set; }
    public Cache2022? Data2022 { get; private set; }
    public bool IsLoaded => Data2026 != null && Data2022 != null;

    private readonly string _cacheDir;
    private readonly string _inferenceScript;
    private readonly ILogger<PredictionCache> _logger;

    public PredictionCache(IConfiguration config, ILogger<PredictionCache> logger)
    {
        _logger = logger;
        var backendDir = Path.GetDirectoryName(typeof(PredictionCache).Assembly.Location)!;
        // Walk up from bin/Debug/net10.0 to backend/
        var dir = new DirectoryInfo(backendDir);
        while (dir != null && dir.Name != "WorldCup.Api")
            dir = dir.Parent;
        var apiDir = dir?.FullName ?? backendDir;
        var backendRoot = Path.GetDirectoryName(apiDir)!;

        _cacheDir = Path.Combine(backendRoot, "cache");
        _inferenceScript = Path.Combine(backendRoot, "python_inference", "inference.py");
        Directory.CreateDirectory(_cacheDir);
    }

    public async Task InitializeAsync()
    {
        var path2026 = Path.Combine(_cacheDir, "predictions_2026.json");
        var path2022 = Path.Combine(_cacheDir, "predictions_2022.json");

        bool needsRegen = !File.Exists(path2026) || !File.Exists(path2022) ||
                          (DateTime.UtcNow - File.GetLastWriteTimeUtc(path2026)).TotalHours > 24;

        if (needsRegen)
        {
            _logger.LogInformation("Running Python inference script...");
            await RunInferenceAsync();
        }
        else
        {
            _logger.LogInformation("Using cached predictions (< 24h old).");
        }

        await LoadFromDiskAsync(path2026, path2022);
    }

    public async Task RefreshAsync()
    {
        _logger.LogInformation("Refreshing predictions cache...");
        await RunInferenceAsync();
        var path2026 = Path.Combine(_cacheDir, "predictions_2026.json");
        var path2022 = Path.Combine(_cacheDir, "predictions_2022.json");
        await LoadFromDiskAsync(path2026, path2022);
    }

    private async Task RunInferenceAsync()
    {
        var psi = new ProcessStartInfo
        {
            FileName = "python3",
            Arguments = $"\"{_inferenceScript}\"",
            WorkingDirectory = Path.GetDirectoryName(Path.GetDirectoryName(_inferenceScript))!,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };

        using var proc = Process.Start(psi) ?? throw new InvalidOperationException("Failed to start python3");
        var stdout = await proc.StandardOutput.ReadToEndAsync();
        var stderr = await proc.StandardError.ReadToEndAsync();
        await proc.WaitForExitAsync();

        if (!string.IsNullOrWhiteSpace(stderr))
            _logger.LogInformation("Inference stderr: {Stderr}", stderr);
        if (!string.IsNullOrWhiteSpace(stdout))
            _logger.LogInformation("Inference stdout: {Stdout}", stdout);

        if (proc.ExitCode != 0)
            throw new InvalidOperationException($"Inference script exited with code {proc.ExitCode}. Stderr: {stderr}");
    }

    private async Task LoadFromDiskAsync(string path2026, string path2022)
    {
        await using var s1 = File.OpenRead(path2026);
        Data2026 = await JsonSerializer.DeserializeAsync<Cache2026>(s1, JsonOpts)
                   ?? throw new InvalidOperationException("Failed to deserialize predictions_2026.json");

        await using var s2 = File.OpenRead(path2022);
        Data2022 = await JsonSerializer.DeserializeAsync<Cache2022>(s2, JsonOpts)
                   ?? throw new InvalidOperationException("Failed to deserialize predictions_2022.json");

        _logger.LogInformation("Cache loaded: {Count2026} 2026 matches, {Count2022} 2022 matches",
            Data2026.Matches.Count, Data2022.Matches.Count);
    }
}
