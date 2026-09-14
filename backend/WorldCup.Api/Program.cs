using WorldCup.Api;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton<PredictionCache>();
builder.Services.AddCors(opts =>
    opts.AddDefaultPolicy(p => p.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()));

var app = builder.Build();
app.UseCors();

// Initialize cache on startup
var cache = app.Services.GetRequiredService<PredictionCache>();
await cache.InitializeAsync();

// ── Health ───────────────────────────────────────────────────────────────────
app.MapGet("/api/health", (PredictionCache c) => Results.Ok(new
{
    status = "ok",
    predictions_loaded = c.IsLoaded,
    model_accuracy = 0.578,
}));

// ── 2026 match list ───────────────────────────────────────────────────────────
app.MapGet("/api/predictions/2026", (PredictionCache c) =>
{
    if (c.Data2026 is null) return Results.Problem("Cache not loaded");
    return Results.Ok(c.Data2026);
});

// ── 2022 match list ───────────────────────────────────────────────────────────
app.MapGet("/api/predictions/2022", (PredictionCache c) =>
{
    if (c.Data2022 is null) return Results.Problem("Cache not loaded");
    return Results.Ok(c.Data2022);
});

// ── 2026 match detail ─────────────────────────────────────────────────────────
app.MapGet("/api/match/2026/{matchId}", (string matchId, PredictionCache c) =>
{
    if (c.Data2026 is null) return Results.Problem("Cache not loaded");
    var match = c.Data2026.Matches.FirstOrDefault(m =>
        string.Equals(m.MatchId, matchId, StringComparison.OrdinalIgnoreCase));
    return match is null ? Results.NotFound() : Results.Ok(match);
});

// ── 2022 match detail ─────────────────────────────────────────────────────────
app.MapGet("/api/match/2022/{matchId}", (string matchId, PredictionCache c) =>
{
    if (c.Data2022 is null) return Results.Problem("Cache not loaded");
    var match = c.Data2022.Matches.FirstOrDefault(m =>
        string.Equals(m.MatchId, matchId, StringComparison.OrdinalIgnoreCase));
    return match is null ? Results.NotFound() : Results.Ok(match);
});

// ── Teams (2026 qualified) ────────────────────────────────────────────────────
app.MapGet("/api/teams", (PredictionCache c) =>
{
    if (c.Data2026 is null) return Results.Problem("Cache not loaded");

    var teams = c.Data2026.Matches
        .Where(m => m.Status == "predicted")
        .SelectMany(m => new[]
        {
            new { Name = m.Team1.Name, Flag = m.Team1.Flag, Stats = m.TeamStats?.Team1 },
            new { Name = m.Team2.Name, Flag = m.Team2.Flag, Stats = m.TeamStats?.Team2 },
        })
        .GroupBy(t => t.Name)
        .Select(g =>
        {
            var first = g.First();
            return new
            {
                name = first.Name,
                flag = first.Flag,
                eloRating = first.Stats?.EloRating,
                fifaRank = first.Stats?.FifaRank,
                last10Pts = first.Stats?.Last10Pts,
                squadValueM = first.Stats?.SquadValueM,
            };
        })
        .OrderBy(t => t.fifaRank ?? 999)
        .ToList();

    return Results.Ok(teams);
});

// ── Raw fixture data (bracket positions) ─────────────────────────────────────
app.MapGet("/api/fixtures", (IWebHostEnvironment env) =>
{
    var dir = new DirectoryInfo(AppContext.BaseDirectory);
    while (dir != null && dir.Name != "WorldCup.Api") dir = dir.Parent;
    var root = Path.GetDirectoryName(Path.GetDirectoryName(dir?.FullName ?? AppContext.BaseDirectory))!;
    var path = Path.Combine(root, "data", "raw", "openfootball", "worldcup.json");
    if (!File.Exists(path)) return Results.NotFound("Fixture file not found");
    var json = File.ReadAllText(path);
    return Results.Content(json, "application/json");
});

// ── Admin refresh ─────────────────────────────────────────────────────────────
app.MapPost("/api/admin/refresh", async (PredictionCache c) =>
{
    await c.RefreshAsync();
    return Results.Ok(new { status = "refreshed", loaded = c.IsLoaded });
});

app.Run();
