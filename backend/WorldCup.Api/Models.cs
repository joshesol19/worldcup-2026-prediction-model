using System.Text.Json.Serialization;

namespace WorldCup.Api;

public record TeamInfo(string Name, string Flag);

public record Probabilities(
    [property: JsonPropertyName("team1Win")] double Team1Win,
    [property: JsonPropertyName("draw")] double Draw,
    [property: JsonPropertyName("team2Win")] double Team2Win
);

public record ShapFeature(string Feature, string RawFeature, string Direction, double Magnitude);

public record TeamStats(
    double? EloRating,
    int? FifaRank,
    int? Last10Pts,
    int? Last5Gd,
    double? SquadValueM
);

public record TeamStatsPair(TeamStats Team1, TeamStats Team2);

public record Score(int? Team1, int? Team2);

// 2026 match (list view)
public record Match2026(
    string MatchId,
    string Date,
    string Time,
    string Venue,
    string Group,
    string Round,
    string Stage,
    TeamInfo Team1,
    TeamInfo Team2,
    string Status,
    Probabilities? Probabilities,
    string? PredictedOutcome,
    string? Confidence,
    List<ShapFeature> ShapFeatures,
    TeamStatsPair? TeamStats,
    int? Neutral
);

// 2022 match
public record Match2022(
    string MatchId,
    string Date,
    string Group,
    string Round,
    string Stage,
    TeamInfo Team1,
    TeamInfo Team2,
    Probabilities? Probabilities,
    string? PredictedOutcome,
    string? ActualOutcome,
    Score? ActualScore,
    string? PredictionStatus,
    string? Confidence,
    List<ShapFeature> ShapFeatures,
    TeamStatsPair? TeamStats
);

public record Cache2026(
    string GeneratedAt,
    int MatchCount,
    double ModelAccuracy,
    List<Match2026> Matches,
    List<Match2026> BracketMatches
);

public record Cache2022(
    string GeneratedAt,
    int MatchCount,
    double ModelAccuracy,
    double ComputedAccuracy,
    Summary2022 Summary,
    List<Match2022> Matches
);

public record Summary2022(int Correct, int Incorrect, int DrawMiss, int Total);
